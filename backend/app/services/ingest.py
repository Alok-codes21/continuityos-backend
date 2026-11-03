"""Ingestion pipeline (plan 1.3): fetch (done by connector) -> permission/selection check -> dedupe -> secret/PII redaction
-> injection flag -> extract -> provenance -> embed -> claims/ledger -> graph."""
import hashlib
import re

from .. import models as m
from . import claims_engine, graph, ledger
from .embed import embed
from .extract import extract, person_key
from .redact import looks_like_injection, looks_confidential, redact


def chunk_text(text, size=700):
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n(?=\[page )", text) if p.strip()]
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 1 <= size:
            cur = (cur + "\n" + p).strip()
        else:
            if cur:
                out.append(cur)
            while len(p) > size:
                out.append(p[:size])
                p = p[size:]
            cur = p
    if cur:
        out.append(cur)
    return out or ([text[:size]] if text.strip() else [])


def locate(content: str, excerpt: str):
    idx = content.find(excerpt)
    if idx < 0:
        return "", False
    line = content.count("\n", 0, idx) + 1
    page = None
    for mm in re.finditer(r"\[page (\d+)\]", content[: idx + 1]):
        page = mm.group(1)
    return (f"page {page}, line {line}" if page else f"line {line}"), True


def selection_allows(rec, selections):
    """selections: SourceSelection rows for this source_ref. No rows = everything selected explicitly by the sync call.
    A record is allowed when ANY included selection matches it (several selections widen, they do not stack)."""
    if not selections:
        return True
    for s in selections:
        if not s.included:
            continue
        if rec.occurred_at and ((s.date_from and rec.occurred_at < s.date_from) or (s.date_to and rec.occurred_at > s.date_to)):
            continue
        if s.content_types and rec.record_type not in s.content_types:
            continue
        return True
    return False


def _upsert_claim(db, project, rec, item, quote_ok, location, author_user):
    status = item.status if quote_ok else "inferred"
    existing = db.query(m.Claim).filter_by(project_id=project.id, subject_key=item.subject_key).all()
    for c in existing:
        if c.statement.strip().lower() == item.statement.strip().lower():
            if not db.query(m.EvidenceLink).filter_by(claim_id=c.id, record_id=rec.id).first():
                db.add(m.EvidenceLink(claim_id=c.id, record_id=rec.id, excerpt=item.excerpt[:500], location=location, quote_verified=quote_ok))
            return c, False
    details = {**item.details, "base_status": status, "source_title": rec.title, "source_type": rec.source_type,
               "author": rec.author}
    c = m.Claim(project_id=project.id, category=item.category, subject_key=item.subject_key, statement=item.statement[:1000],
                details=details, status=status, created_by="system")
    db.add(c)
    db.flush()
    db.add(m.EvidenceLink(claim_id=c.id, record_id=rec.id, excerpt=item.excerpt[:500], location=location, quote_verified=quote_ok))
    ledger.append(db, project.id, "claim_created", "claim", c.id, actor=rec.author, record_id=rec.id, source_id=rec.source_id,
                  new_state={"category": c.category, "status": status}, verification=status, occurred_at=rec.occurred_at,
                  permission=rec.visibility)
    return c, True


def _side_tables(db, project, rec, item, claim):
    d = item.details
    comp_name = d.get("component_name") or d.get("component")
    if item.category in ("component",):
        claims_engine.upsert_component(db, project.id, d["component"])
    if item.category == "owner":
        claims_engine.upsert_component(db, project.id, d.get("component_name") or d["component"])
    if item.category == "api" and d.get("component"):
        claims_engine.upsert_component(db, project.id, d["component"])
    if item.category == "dependency":
        claims_engine.upsert_component(db, project.id, d["from"])
        claims_engine.upsert_component(db, project.id, d["to"])
    if item.category == "decision" and not db.query(m.Decision).filter_by(project_id=project.id, claim_id=claim.id).first():
        people = []
        for nm in [d.get("decided_by"), rec.author, *re.findall(r"@([A-Za-z0-9_.-]{2,40})", f"{item.statement} {item.excerpt}")]:
            if nm and nm not in people:
                people.append(nm)
        claim.details = {**claim.details, "participants": people}
        db.add(m.Decision(project_id=project.id, claim_id=claim.id, title=item.statement[:500], decided_by=d.get("decided_by"), participants=people,
                          alternatives=d.get("alternatives", []), rationale=d.get("rationale", ""), decided_at=rec.occurred_at or m.now(),
                          record_id=rec.id))
    if item.category == "task" and not db.query(m.Task).filter_by(project_id=project.id, title=item.statement[:500]).first():
        db.add(m.Task(project_id=project.id, title=item.statement[:500], assignee_key=person_key(d["assignee"]) if d.get("assignee") else None,
                      status="done" if d.get("done") else "open", record_id=rec.id))


def ingest_records(db, project, source, records, actor=None, selections=None, job=None, allowed_types=None):
    job = job or m.SourceSyncJob(project_id=project.id, source_id=source.id if source else None)
    db.add(job)
    db.flush()
    opted_out = {c.author.lower() for c in db.query(m.ContributorConsent).filter_by(project_id=project.id, granted=False)}
    opted_in = {c.author.lower() for c in db.query(m.ContributorConsent).filter_by(project_id=project.id, granted=True)}
    opt_in_mode = getattr(project, "consent_mode", "opt_out") == "opt_in"
    for r in records:
        job.fetched += 1
        if not selection_allows(r, selections):
            continue
        if allowed_types is not None and r.record_type not in allowed_types:
            continue  # integration scope was not approved for this kind of record
        if r.author and r.author.lower() in opted_out:
            continue  # individual withdrew consent for their contributions
        if opt_in_mode and r.record_type != "document" and (not r.author or r.author.lower() not in opted_in):
            continue  # opt-in project: only people who explicitly said yes are ingested (uploaded documents are added by a manager)
        clean, findings = redact(r.content)
        title, tfind = redact(r.title or "")
        injected = looks_like_injection(r.content) or looks_like_injection(r.title or "")
        h = hashlib.sha256((r.source_type + "\n" + clean).encode()).hexdigest()
        if db.query(m.SourceRecord.id).filter_by(project_id=project.id, content_hash=h).first():
            job.duplicates += 1
            continue
        prev = db.query(m.SourceRecord).filter_by(project_id=project.id, source_type=r.source_type, external_id=r.external_id).order_by(m.SourceRecord.version.desc()).first()
        rec = m.SourceRecord(org_id=project.org_id, project_id=project.id, source_id=source.id if source else None, source_type=r.source_type,
                             external_id=r.external_id, record_type=r.record_type, title=title[:500], content=clean, author=r.author,
                             url=r.url, occurred_at=r.occurred_at or m.now(), content_hash=h, redactions=len(findings) + len(tfind),
                             injection_suspected=injected, version=(prev.version + 1) if prev else 1,
                             visibility="restricted" if (looks_confidential(clean) or (r.meta or {}).get("visibility") == "restricted") else "project",
                             processing_status="flagged" if injected else "processed")
        db.add(rec)
        db.flush()
        job.stored += 1
        job.redactions += rec.redactions
        for i, ch in enumerate(chunk_text(clean)):
            db.add(m.DocumentChunk(project_id=project.id, record_id=rec.id, position=i, text=ch, embedding=embed(ch)))
        if injected:
            job.flagged += 1
            ledger.append(db, project.id, "record_flagged", "record", rec.id, actor="system", record_id=rec.id,
                          new_state={"reason": "possible_prompt_injection"}, verification="inferred", permission=rec.visibility)
            continue  # flagged content is kept for reviewers but never extracted from
        if r.author:
            graph.ensure_person(db, project.id, r.author)
        for item in extract(r.record_type, title, clean, r.author, r.meta):
            location, ok = locate(clean, item.excerpt)
            claim, _ = _upsert_claim(db, project, rec, item, ok, location, actor)
            _side_tables(db, project, rec, item, claim)
    job.status = "completed"
    job.finished_at = m.now()
    db.flush()
    claims_engine.reconcile(db, project.id)
    graph.rebuild_graph(db, project.id)
    db.flush()
    return job
