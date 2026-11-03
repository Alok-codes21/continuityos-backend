"""Claim state machine: conflicts, staleness, supersession, missing knowledge and gap generation.
All derived states are recomputed from stored claims + evidence; nothing is hardcoded."""
import re
from datetime import timedelta

from .. import models as m
from ..config import settings
from . import ledger
from .extract import comp_base

TRUST_FINAL = ("verified",)
SERVICE_KINDS = ("service", "api", "worker", "gateway", "pipeline", "db", "dashboard")


def comp_kind(name: str) -> str:
    n = (name or "").lower()
    for k in SERVICE_KINDS:
        if n.endswith("-" + k):
            return k
    return "module"


def upsert_component(db, project_id, name):
    base = comp_base(name)
    c = db.query(m.Component).filter_by(project_id=project_id, key=base).first()
    if not c:
        c = m.Component(project_id=project_id, key=base, name=name, kind=comp_kind(name))
        db.add(c)
        db.flush()
    elif comp_kind(name) != "module" and c.kind == "module":
        c.name, c.kind = name, comp_kind(name)
    return c


def latest_evidence_time(db, claim):
    rows = (db.query(m.SourceRecord.occurred_at).join(m.EvidenceLink, m.EvidenceLink.record_id == m.SourceRecord.id)
            .filter(m.EvidenceLink.claim_id == claim.id).all())
    return max((r[0] for r in rows if r[0]), default=None)


def _sig(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


def reconcile(db, project_id, now_=None):
    now_ = now_ or m.now()
    claims = db.query(m.Claim).filter(m.Claim.project_id == project_id).all()
    live = [c for c in claims if not c.details.get("manual_status") and not c.created_by.startswith("system:missing")]

    # 1. reset derived states of system claims that humans have not verified
    for c in live:
        if c.status == "verified":
            continue
        base = c.details.get("base_status") or c.status
        c.details = {**c.details, "base_status": base}
        c.status, c.freshness, c.superseded_by = base, "current", None

    # 2. explicit supersession between decisions (newer decision text names the older one)
    decisions = [c for c in claims if c.category == "decision" and c.status != "verified" or c.category == "decision"]
    decisions.sort(key=lambda c: (latest_evidence_time(db, c) or c.created_at, c.created_at))
    for newer in decisions:
        phrase = (newer.details.get("supersedes") or "").strip()
        if not phrase:
            continue
        want = _sig(phrase)
        for older in decisions:
            if older.id == newer.id or older.status == "superseded":
                continue
            if want and want <= _sig(older.statement) and (latest_evidence_time(db, older) or older.created_at) <= (latest_evidence_time(db, newer) or newer.created_at):
                older.status, older.freshness, older.superseded_by = "superseded", "superseded", newer.id
                dec = db.query(m.Decision).filter_by(project_id=project_id, claim_id=older.id).first()
                if dec:
                    dec.status, dec.superseded_by = "superseded", newer.id

    # 3. conflicts on config values (e.g. runbook says 3 retries, code says 5)
    groups = {}
    for c in claims:
        if c.category == "config_value" and c.status != "superseded":
            groups.setdefault(c.subject_key, []).append(c)
    for key, cs in groups.items():
        vals = {str(c.details.get("value")) for c in cs}
        if len(vals) <= 1:
            continue
        verified = [c for c in cs if c.status == "verified"]
        for c in cs:
            if c.status == "verified":
                continue
            if verified and str(c.details.get("value")) != str(verified[0].details.get("value")):
                c.status, c.freshness = "outdated", "stale"
            elif not verified:
                c.status = "conflicting"

    # 4. staleness by evidence age
    cutoff = now_ - timedelta(days=settings.outdated_days)
    for c in claims:
        if c.status in ("superseded",) or c.created_by.startswith("system:missing"):
            continue
        t = latest_evidence_time(db, c)
        if t and t < cutoff:
            c.freshness = "stale" if c.freshness == "current" else c.freshness
            if c.status in ("evidence_backed", "inferred"):
                c.status = "outdated"
        c.updated_at = now_

    # 5. source still current? A newer version of the same source record that no longer contains the quoted text
    for c in claims:
        if c.status in ("superseded",) or c.created_by.startswith("system:missing") or c.details.get("draft"):
            continue
        for ev in db.query(m.EvidenceLink).filter_by(claim_id=c.id).all():
            rec = db.get(m.SourceRecord, ev.record_id) if ev.record_id else None
            if not rec or not ev.excerpt:
                continue
            newest = (db.query(m.SourceRecord).filter_by(project_id=project_id, source_type=rec.source_type, external_id=rec.external_id)
                      .order_by(m.SourceRecord.version.desc()).first())
            if newest and newest.version > rec.version and ev.excerpt not in (newest.content or ""):
                if c.status == "verified":
                    c.details = {**c.details, "needs_reverification": True, "source_changed": True}
                    c.freshness = "stale"
                elif c.status in ("evidence_backed", "inferred"):
                    c.status, c.freshness = "outdated", "stale"
                    c.details = {**c.details, "source_changed": True}
                break
    db.flush()
    return rebuild_gaps(db, project_id)


def _claims(db, project_id, category, statuses=None):
    q = db.query(m.Claim).filter_by(project_id=project_id, category=category)
    cs = q.all()
    return [c for c in cs if statuses is None or c.status in statuses]


def rebuild_gaps(db, project_id):
    desired = {}  # (gap_type, entity_key) -> dict
    comps = db.query(m.Component).filter_by(project_id=project_id).all()
    owners = _claims(db, project_id, "owner", ("verified", "evidence_backed"))
    owned = {c.details.get("component") for c in owners}
    procs = _claims(db, project_id, "procedure", ("verified", "evidence_backed", "inferred"))
    have_roll = {(c.details.get("component"), c.details.get("topic")) for c in procs if not c.created_by.startswith("system:missing")}
    for comp in comps:
        if comp.key not in owned:
            desired[("no_documented_owner", comp.key)] = dict(
                entity_type="component", description=f"No documented owner for {comp.name}",
                found="No owner statement or CODEOWNERS entry was found in authorised sources.",
                recommended_action=f"Ask the team who owns {comp.name} and record it.")
        if comp.kind in SERVICE_KINDS and (comp.key, "rollback") not in have_roll:
            desired[("missing_procedure", f"{comp.key}:rollback")] = dict(
                entity_type="component", description=f"No verified rollback procedure for {comp.name}",
                found="Component is known but no rollback procedure was found in authorised documentation.",
                recommended_action=f"Ask the previous owner of {comp.name} to describe and verify the rollback steps.")
    rationale_verified = {c.subject_key.replace("rationale:", "", 1) for c in _claims(db, project_id, "rationale", ("verified",))}
    for d in _claims(db, project_id, "decision"):
        if d.status in ("superseded",):
            continue
        if not d.details.get("rationale") and d.subject_key not in rationale_verified:
            desired[("undocumented_decision", d.subject_key)] = dict(
                entity_type="decision", description=f"Decision without recorded reasoning: {d.statement[:120]}",
                found="The decision exists in the sources but no reasoning was recorded.",
                recommended_action="Ask the decision maker why this was decided and what alternatives were considered.")
    groups = {}
    for c in _claims(db, project_id, "config_value", ("conflicting",)):
        groups.setdefault(c.subject_key, []).append(c)
    for key, cs in groups.items():
        found = "; ".join(f"{c.details.get('value')} ({(c.details.get('source_title') or 'source')})" for c in cs)
        desired[("conflict", key)] = dict(
            entity_type="claim", description=f"Conflicting values for {key.split(':',1)[1].replace(':', ' ')}",
            found=f"Sources disagree: {found}",
            recommended_action="Ask the owner which is authoritative, update the stale source, then mark the claim Verified.")
    for b in _claims(db, project_id, "bug"):
        if not b.details.get("resolved") and b.status != "superseded":
            desired[("unresolved_bug", b.subject_key)] = dict(
                entity_type="bug", description=f"Unresolved: {b.statement[:120]}", found="No fix or resolution found in sources.",
                recommended_action="Confirm status and who is working on it.")

    existing = {(g.gap_type, g.entity_key): g for g in db.query(m.KnowledgeGap).filter_by(project_id=project_id).all()}
    for k, g in existing.items():
        if k in desired:
            if g.status == "resolved":
                g.status = "open"
            for f, v in desired[k].items():
                setattr(g, f, v)
        elif g.status == "open":
            g.status = "resolved"
    for (gt, ek), d in desired.items():
        if (gt, ek) not in existing:
            db.add(m.KnowledgeGap(project_id=project_id, gap_type=gt, entity_key=ek, **d))

    # Missing claims mirror the gaps that are about absent knowledge
    wanted_missing = {}
    for (gt, ek), d in desired.items():
        if gt == "missing_procedure":
            comp = ek.split(":")[0]
            wanted_missing[f"procedure:{comp}:rollback"] = ("procedure", d["description"], {"component": comp, "topic": "rollback"})
        elif gt == "undocumented_decision":
            wanted_missing[f"rationale:{ek}"] = ("rationale", "Reasoning missing: " + d["description"].split(": ", 1)[-1], {"decision": ek})
    missing_existing = {c.subject_key: c for c in db.query(m.Claim).filter(m.Claim.project_id == project_id, m.Claim.status == "missing").all()}
    for key, (cat, text, det) in wanted_missing.items():
        if key not in missing_existing:
            real = db.query(m.Claim).filter(m.Claim.project_id == project_id, m.Claim.subject_key == key, m.Claim.status != "missing").first()
            if real:
                continue
            c = m.Claim(project_id=project_id, category=cat, subject_key=key, statement=text, details=det, status="missing",
                        created_by="system:missing")
            db.add(c)
            db.flush()
            ledger.append(db, project_id, "knowledge_missing", "claim", c.id, actor="system", new_state={"status": "missing"}, verification="missing")
    for key, c in missing_existing.items():
        if key not in wanted_missing:
            db.delete(c)
    db.flush()
    return {"gaps_open": sum(1 for _ in desired)}
