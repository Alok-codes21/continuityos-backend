"""Handover document: 7 sections, every item cites evidence, versions, manager approval, PDF export."""
import io
import re

from fastapi import HTTPException

from .. import models as m
from . import access, graph, ledger, risk

SECTIONS = [("summary", "Summary of responsibilities"), ("ownership", "Ownership and backups"), ("systems", "Systems and dependencies"),
            ("decisions", "Decisions and reasoning"), ("procedures", "Procedures and runbooks"), ("open_work", "Open work and risks"),
            ("gaps", "Knowledge still missing"),
            ("contacts", "Important contacts"), ("deployment", "Deployment and release instructions"), ("first_actions", "Recommended first actions"), ("limitations", "Known limitations of this handover")]


def _evidence(db, claim, role):
    out = []
    for ev in db.query(m.EvidenceLink).filter_by(claim_id=claim.id).all():
        if ev.record_id:
            r = db.get(m.SourceRecord, ev.record_id)
            if not r or not access.visible_record(r, role):
                continue
            out.append({"source": r.title, "type": r.source_type, "location": ev.location, "quote": ev.excerpt, "url": r.url, "verified_quote": ev.quote_verified})
        else:
            out.append({"source": "Interview answer", "type": "interview", "location": ev.location, "quote": ev.excerpt, "verified_quote": True})
    return out


def _relevant(role_profile, *texts):
    if not role_profile:
        return True
    words = [w for w in role_profile.lower().replace(",", " ").split() if len(w) > 2]
    t = " ".join(texts).lower()
    return any(w in t for w in words) if words else True


def generate(db, project, person_key_, user, role, incoming_user_id=None, role_profile=""):
    p = graph.resolve_person(db, project.id, person_key_)
    if not p:
        raise HTTPException(404, "Person not found")
    sim = risk.simulate(db, project.id, p.key, persist=False)
    comps = {r["key"] for r in sim["components"]}
    live = [c for c in access.visible_claims(db, project.id, role) if c.status != "superseded"]
    ver = {c.status for c in live}
    items = []

    def add(section, title, body, claim=None, status=None):
        items.append({"section": section, "title": title[:300], "body": body[:2000], "status": status or (claim.status if claim else "derived"),
                      "claim_id": claim.id if claim else None, "evidence": _evidence(db, claim, role) if claim else []})

    for r in sim["components"]:
        add("summary", f"{r['component']}", f"{p.name} holds this as: {', '.join(r['roles'])}. Dependents: {', '.join(r['dependents']) or 'none recorded'}.")
    for c in live:
        d = c.details
        if c.details.get("draft"):
            continue
        comp = d.get("component") or d.get("from")
        if c.category in ("owner", "holder", "backup") and comp in comps and _relevant(role_profile, c.statement, comp):
            add("ownership", c.statement, "Ownership record.", c)
        elif c.category == "dependency" and (comp in comps or d.get("to") in comps):
            add("systems", c.statement, "Dependency recorded in sources.", c)
        elif c.category == "api" and comp in comps:
            add("systems", c.statement, "API endpoint.", c)
        elif c.category == "decision" and (comp in comps or graph.norm_person(d.get("decided_by")) == p.key):
            add("decisions", c.statement, f"Reasoning: {d.get('rationale') or 'not recorded yet'}. Alternatives: {', '.join(d.get('alternatives') or []) or 'none recorded'}. Participants: {', '.join(d.get('participants') or []) or 'not recorded'}. Still valid: {'no, superseded' if c.status == 'superseded' else 'yes' if c.status != 'outdated' else 'unclear, source is outdated'}.", c)
        elif c.category == "rationale" and c.status != "missing":
            add("decisions", f"Reasoning for {c.subject_key.split(':', 1)[1][:60]}", c.statement, c)
        elif c.category == "procedure" and c.status != "missing" and d.get("component") in comps:
            add("procedures", f"{d.get('topic', 'procedure')} for {d.get('component')}", c.statement, c)
        elif c.category in ("task", "bug", "blocker", "risk") and not d.get("done") and not d.get("resolved") and (
                comp in comps or graph.norm_person(d.get("assignee")) == p.key or p.key in [graph.norm_person(a) for a in d.get("assignees") or []]):
            add("open_work", c.statement, f"Open {c.category}.", c)
        elif c.category == "config_value" and c.status == "conflicting" and comp in comps:
            add("open_work", c.statement, "Sources disagree on this value. Not yet resolved.", c)
    for g in db.query(m.KnowledgeGap).filter_by(project_id=project.id, status="open").all():
        if (g.entity_key or "").split(":")[0] in comps:
            add("gaps", g.description, g.found + " " + g.recommended_action, status="missing")
    # contacts: who else holds each component (derived from qualified-holder links)
    for r in sim["components"]:
        if r["remaining_holders"]:
            add("contacts", f"Contact for {r['component']}", f"Ask {', '.join(r['remaining_holders'])} about {r['component']}.")
    # deployment: procedure claims that talk about deploy / release / rollback
    for c in live:
        d = c.details
        if c.category == "procedure" and not d.get("draft") and c.status != "missing" and d.get("component") in comps and \
                re.search(r"(?i)deploy|release|rollback|ship|pipeline|ci/cd", f"{d.get('topic', '')} {c.statement}"):
            add("deployment", f"{d.get('topic', 'deployment')} for {d.get('component')}", c.statement, c)
    # known limitations: what this document cannot vouch for
    unverified = [c for c in live if c.status in ("inferred", "outdated", "conflicting") and not c.details.get("draft")]
    stale = [c for c in live if c.details.get("needs_reverification") or c.freshness == "stale"]
    flagged_recs = db.query(m.SourceRecord).filter_by(project_id=project.id, injection_suspected=True).all()
    flagged = len(flagged_recs)
    redacted_recs = [r for r in db.query(m.SourceRecord).filter_by(project_id=project.id) if r.redactions]
    redacted = sum(r.redactions or 0 for r in redacted_recs)
    if unverified:
        add("limitations", f"{len(unverified)} item(s) are not verified", "These are inferred, outdated or conflicting. Treat them as leads, not facts.", status="inferred")
        for c in unverified:
            add("limitations", c.statement[:120], f"Not verified ({c.status}). Re-verify before relying on it.", c, status=c.status)
    if stale:
        add("limitations", f"{len(stale)} item(s) may be out of date", "Their sources are old or changed since. Re-verify before relying on them.", status="outdated")
        for c in stale:
            add("limitations", c.statement[:120], "May be out of date: the source is old or changed. Re-verify before relying on it.", c, status="outdated")
    if flagged:
        add("limitations", f"{flagged} source record(s) were excluded", "They looked like prompt-injection attempts and were not used.", status="derived")
        for r in flagged_recs:
            add("limitations", f"Excluded: {(r.title or r.external_id or 'record')[:110]}", "This source record looked like a prompt-injection attempt and was not used.", status="derived")
    if redacted:
        add("limitations", f"{redacted} secret/personal value(s) were redacted", "Credentials and emails are masked, so some details are intentionally absent.", status="derived")
        for r in redacted_recs:
            add("limitations", f"Redacted: {(r.title or r.external_id or 'record')[:110]}", f"{r.redactions} secret/personal value(s) in this record are masked.", status="derived")
    add("limitations", "Coverage", "Only connected and selected sources, and only contributors who consented, are covered. Anything discussed elsewhere is not here.", status="derived")
    # first actions: derived from the risks and open gaps found above
    for r in sim["components"]:
        if not r["remaining_holders"]:
            add("first_actions", f"Take ownership of {r['component']}", f"Nobody else is a qualified holder of {r['component']}. Get the owner statement confirmed first.")
    for it in [i for i in items if i["section"] == "open_work"][:3]:
        add("first_actions", f"Pick up: {it['title'][:120]}", "Open item assigned to or touching this person.")
    for it in [i for i in items if i["section"] == "gaps"][:3]:
        add("first_actions", f"Close gap: {it['title'][:120]}", "Ask the departing person to answer this before they leave.")
    last = db.query(m.Handover).filter_by(project_id=project.id, departing_person_key=p.key).count()
    h = m.Handover(project_id=project.id, departing_person_key=p.key, incoming_user_id=incoming_user_id, role_profile=role_profile,
                   generated_by=user.id, summary={"version": last + 1, "status": "draft", "risk_level": sim["level"],
                                                  "holder_definition": risk.HOLDER_DEFINITION})
    db.add(h)
    db.flush()
    for it in items:
        db.add(m.HandoverItem(handover_id=h.id, **it))
    ledger.append(db, project.id, "handover_generated", "handover", h.id, actor=user.id, new_state={"version": last + 1, "items": len(items)})
    db.flush()
    return h


def to_dict(db, h, with_items=True):
    d = {"id": h.id, "person_key": h.departing_person_key, "role_profile": h.role_profile, "summary": h.summary, "created_at": h.created_at.isoformat()}
    if with_items:
        its = db.query(m.HandoverItem).filter_by(handover_id=h.id).all()
        d["sections"] = [{"key": k, "title": t, "items": [{"id": i.id, "title": i.title, "body": i.body, "status": i.status, "claim_id": i.claim_id,
                                                           "evidence": i.evidence} for i in its if i.section == k]} for k, t in SECTIONS]
    return d


def request_approval(db, project, h, user):
    if (h.summary or {}).get("status") == "approved":
        raise HTTPException(409, "Already approved")
    ap = m.Approval(project_id=project.id, kind="handover_doc", target_id=h.id, status="pending",
                    payload={"person": h.departing_person_key, "version": h.summary.get("version")}, requested_by=user.id)
    db.add(ap)
    db.flush()
    return ap


def approve(db, project, ap, approver):
    h = db.get(m.Handover, ap.target_id)
    if not h or h.project_id != project.id:
        raise HTTPException(404, "Not found")
    h.summary = {**h.summary, "status": "approved", "approved_by": approver.id}
    ledger.append(db, project.id, "handover_approved", "handover", h.id, actor=approver.id, verification="verified")


def pdf(db, h, project_name):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    ss = getSampleStyleSheet()
    d = to_dict(db, h)
    st = [Paragraph(escape(f"Handover: {h.departing_person_key} ({project_name})"), ss["Title"]),
          Paragraph(escape(f"Version {h.summary.get('version')} - {h.summary.get('status')} - risk {h.summary.get('risk_level')}"), ss["Normal"]), Spacer(1, 12)]
    for s in d["sections"]:
        st.append(Paragraph(escape(s["title"]), ss["Heading2"]))
        if not s["items"]:
            st.append(Paragraph("Nothing recorded.", ss["Italic"]))
        for it in s["items"]:
            st.append(Paragraph(escape(f"<b>{it['title']}</b> [{it['status']}]").replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>"), ss["Normal"]))
            st.append(Paragraph(escape(it["body"]), ss["Normal"]))
            for ev in it["evidence"][:3]:
                st.append(Paragraph(escape(f"Evidence: {ev['source']} ({ev.get('location') or ''}): \"{(ev.get('quote') or '')[:160]}\""), ss["Italic"]))
            st.append(Spacer(1, 6))
    doc.build(st)
    return buf.getvalue()
