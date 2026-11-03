import os
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..connectors import catalog
from ..connectors.base import ConnectorError, ConnectorRateLimited, ConnectorUnavailable
from ..connectors.manual_upload import ManualUploadConnector, extract_text
from ..db import get_db
from ..security import ROLE_RANK, audit, current_user, decrypt_token, encrypt_token, need, org_role
from ..services import access, claims_engine, graph, ingest, ledger

router = APIRouter(prefix="/api", tags=["sources"])
MAX_UPLOAD = 10 * 1024 * 1024
ALLOWED_EXT = {".pdf", ".docx", ".txt", ".md", ".csv"}


def safe_name(name: str) -> str:
    base = os.path.basename((name or "upload").replace("\\", "/"))
    base = re.sub(r"[^A-Za-z0-9._\- ]", "_", base).strip(". ") or "upload"
    return base[:120]


@router.get("/integrations/catalog")
def get_catalog(user: m.User = Depends(current_user)):
    return [{**c, "status": "available" if c["implemented"] else "unavailable"} for c in catalog.CATALOG]


def _org(org_id, db, user, min_role):
    if ROLE_RANK[org_role(db, user, org_id)] < ROLE_RANK[min_role]:
        raise HTTPException(403, f"Requires {min_role} role")


SCOPE_TYPES = {"commits": ("commit",), "pull_requests": ("pull_request",), "issues": ("issue",), "codeowners": ("codeowners",),
               "documents": ("document",), "messages": ("message",), "repo": ("commit", "pull_request", "issue", "codeowners")}


class ConnectIn(BaseModel):
    connector: str
    token: str = Field(default="", max_length=500)
    scopes: dict = {}
    consent: bool = False


@router.get("/orgs/{org_id}/integrations")
def list_integrations(org_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org(org_id, db, user, "contributor")
    return [{"id": i.id, "connector": i.connector, "status": i.status, "scopes": i.scopes, "created_at": i.created_at.isoformat(),
             "revoked_at": i.revoked_at.isoformat() if i.revoked_at else None}
            for i in db.query(m.Integration).filter_by(org_id=org_id)]


@router.post("/orgs/{org_id}/integrations", status_code=201)
def connect(org_id: str, body: ConnectIn, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org(org_id, db, user, "admin")
    entry = next((c for c in catalog.CATALOG if c["id"] == body.connector), None)
    if not entry:
        raise HTTPException(404, "Unknown connector")
    if not entry["implemented"]:
        raise HTTPException(501, f"{entry['name']} is not available yet")
    if not body.consent:
        raise HTTPException(422, "Explicit consent is required before connecting a source")
    conn = catalog.get_connector(body.connector, body.token)
    try:
        if body.connector != "manual_upload":
            if not body.token:
                raise HTTPException(422, "Token required")
            conn.validate_permissions()
    except ConnectorError as e:
        raise HTTPException(400, f"Could not validate access: {e}")
    integ = m.Integration(org_id=org_id, connector=body.connector, encrypted_token=encrypt_token(body.token), scopes=body.scopes, created_by=user.id)
    db.add(integ)
    db.flush()
    db.add(m.ConsentRecord(org_id=org_id, integration_id=integ.id, user_id=user.id, kind="connect", granted=True))
    for s in (body.scopes.get("permissions") or []) if isinstance(body.scopes, dict) else []:
        db.add(m.IntegrationPermission(integration_id=integ.id, scope=str(s)[:100], approved=True))
    audit(db, "integration_connected", user, org_id, target_type="integration", target_id=integ.id, connector=body.connector)
    db.commit()
    return {"id": integ.id, "connector": integ.connector, "status": integ.status}


@router.delete("/orgs/{org_id}/integrations/{integration_id}")
def revoke(org_id: str, integration_id: str, db: Session = Depends(get_db), user: m.User = Depends(current_user)):
    _org(org_id, db, user, "admin")
    i = db.get(m.Integration, integration_id)
    if not i or i.org_id != org_id:
        raise HTTPException(404, "Not found")
    try:
        catalog.get_connector(i.connector, decrypt_token(i.encrypted_token)).revoke_access()
    except ConnectorError:
        pass
    i.status, i.encrypted_token, i.revoked_at = "revoked", "", m.now()
    db.add(m.ConsentRecord(org_id=org_id, integration_id=i.id, user_id=user.id, kind="revoke", granted=False))
    audit(db, "integration_revoked", user, org_id, target_type="integration", target_id=i.id)
    db.commit()
    return {"ok": True, "status": "revoked"}


class SourceIn(BaseModel):
    integration_id: str
    source_ref: str = Field(max_length=300)
    name: str = Field(default="", max_length=300)


def _source(db, ctx, sid):
    s = db.get(m.Source, sid)
    if not s or s.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    return s


@router.get("/projects/{project_id}/sources")
def sources(ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    out = []
    for s in db.query(m.Source).filter_by(project_id=ctx.pid):
        out.append({"id": s.id, "type": s.source_type, "ref": s.external_id, "name": s.name, "integration_id": s.integration_id,
                    "records": db.query(m.SourceRecord).filter_by(source_id=s.id).count(),
                    "selections": [{"id": x.id, "included": x.included, "date_from": x.date_from, "date_to": x.date_to, "content_types": x.content_types}
                                   for x in db.query(m.SourceSelection).filter_by(integration_id=s.integration_id, project_id=ctx.pid, source_ref=s.external_id)]})
    return out


@router.get("/projects/{project_id}/available-sources/{integration_id}")
def available(integration_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    i = db.get(m.Integration, integration_id)
    if not i or i.org_id != ctx.org_id or i.status != "active":
        raise HTTPException(404, "Not found")
    try:
        return catalog.get_connector(i.connector, decrypt_token(i.encrypted_token)).get_available_sources()
    except ConnectorError as e:
        raise HTTPException(502, str(e))


@router.post("/projects/{project_id}/sources", status_code=201)
def add_source(body: SourceIn, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    i = db.get(m.Integration, body.integration_id)
    if not i or i.org_id != ctx.org_id or i.status != "active":
        raise HTTPException(404, "Not found")
    if db.query(m.Source).filter_by(project_id=ctx.pid, integration_id=i.id, external_id=body.source_ref).first():
        raise HTTPException(409, "Source already added")
    s = m.Source(project_id=ctx.pid, integration_id=i.id, source_type=i.connector, external_id=body.source_ref, name=body.name or body.source_ref)
    db.add(s)
    db.flush()
    db.add(m.SourceSelection(integration_id=i.id, project_id=ctx.pid, source_ref=body.source_ref, included=True, content_types=[]))
    audit(db, "source_added", ctx.user, ctx.org_id, ctx.pid, "source", s.id)
    db.commit()
    return {"id": s.id}


class SelectionIn(BaseModel):
    included: bool = True
    date_from: datetime | None = None
    date_to: datetime | None = None
    content_types: list[str] = []


@router.put("/projects/{project_id}/sources/{source_id}/selection")
def set_selection(source_id: str, body: SelectionIn, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    s = _source(db, ctx, source_id)
    sel = db.query(m.SourceSelection).filter_by(integration_id=s.integration_id, project_id=ctx.pid, source_ref=s.external_id).first()
    if not sel:
        sel = m.SourceSelection(integration_id=s.integration_id, project_id=ctx.pid, source_ref=s.external_id)
        db.add(sel)
    sel.included, sel.date_from, sel.date_to, sel.content_types = body.included, body.date_from, body.date_to, body.content_types
    db.flush()
    ledger.append(db, ctx.pid, "scope_changed", "selection", sel.id, actor=ctx.user.id, new_state={"included": sel.included}, verification="verified")
    audit(db, "selection_changed", ctx.user, ctx.org_id, ctx.pid, "source", s.id)
    db.commit()
    return {"id": sel.id, "included": sel.included}


def _job_dict(j):
    return {"id": j.id, "source_id": j.source_id, "status": j.status, "fetched": j.fetched, "stored": j.stored, "duplicates": j.duplicates,
            "redactions": j.redactions, "flagged": j.flagged, "error": j.error, "started_at": j.started_at.isoformat() if j.started_at else None}


@router.post("/projects/{project_id}/sources/{source_id}/sync")
def sync(source_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    s = _source(db, ctx, source_id)
    i = db.get(m.Integration, s.integration_id)
    if not i or i.status != "active":
        raise HTTPException(409, "Integration is revoked")
    job = m.SourceSyncJob(project_id=ctx.pid, source_id=s.id, status="running")
    db.add(job)
    db.flush()
    sels = db.query(m.SourceSelection).filter_by(integration_id=i.id, project_id=ctx.pid, source_ref=s.external_id).all()
    try:
        conn = catalog.get_connector(i.connector, decrypt_token(i.encrypted_token))
        records = conn.fetch_records(s.external_id, cursor=s.last_cursor)
    except ConnectorRateLimited as e:
        job.status, job.error = "rate_limited", str(e)
        db.commit()
        raise HTTPException(429, str(e))
    except ConnectorError as e:
        job.status, job.error = "failed", str(e)[:500]
        db.commit()
        raise HTTPException(502, "Source fetch failed")
    scopes = [p.scope for p in db.query(m.IntegrationPermission).filter_by(integration_id=i.id, approved=True)]
    allowed = None
    if scopes:
        allowed = {t for sc in scopes for t in SCOPE_TYPES.get(sc, ())}
    ingest.ingest_records(db, ctx.project, s, records, actor=ctx.user, selections=sels, job=job, allowed_types=allowed)
    if getattr(conn, "warnings", None):
        job.error = "partial: " + "; ".join(conn.warnings)[:450]
    s.last_cursor = datetime.utcnow().isoformat()
    audit(db, "source_synced", ctx.user, ctx.org_id, ctx.pid, "source", s.id, stored=job.stored)
    db.commit()
    return _job_dict(job)


@router.get("/projects/{project_id}/sync-jobs")
def jobs(ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    return [_job_dict(j) for j in db.query(m.SourceSyncJob).filter_by(project_id=ctx.pid).order_by(m.SourceSyncJob.started_at.desc()).limit(100)]


@router.post("/projects/{project_id}/uploads", status_code=201)
async def upload(file: UploadFile = File(...), visibility: str = Form("project"), author: str = Form(""),
                 ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    name = safe_name(file.filename)
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(415, f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXT))}")
    if visibility not in ("project", "restricted"):
        raise HTTPException(422, "Invalid visibility")
    if visibility == "restricted" and ROLE_RANK[ctx.org_role] < ROLE_RANK["manager"]:
        raise HTTPException(403, "Only managers can upload restricted documents")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File too large (10 MB max)")
    try:
        text = extract_text(name, data)
    except Exception:
        raise HTTPException(422, "Could not read this file")
    if not text.strip():
        raise HTTPException(422, "No text found in file")
    integ = db.query(m.Integration).filter_by(org_id=ctx.org_id, connector="manual_upload", status="active").first()
    if not integ:
        integ = m.Integration(org_id=ctx.org_id, connector="manual_upload", created_by=ctx.user.id)
        db.add(integ)
        db.flush()
    src = db.query(m.Source).filter_by(project_id=ctx.pid, source_type="manual_upload").first()
    if not src:
        src = m.Source(project_id=ctx.pid, integration_id=integ.id, source_type="manual_upload", external_id="uploads", name="File uploads")
        db.add(src)
        db.flush()
    rec = ManualUploadConnector().normalize_record({"filename": name, "text": text, "author": author or None, "occurred_at": m.now()})
    rec.meta = {"visibility": visibility}
    job = ingest.ingest_records(db, ctx.project, src, [rec], actor=ctx.user)
    srec = db.query(m.SourceRecord).filter_by(project_id=ctx.pid, source_id=src.id, external_id=name).order_by(m.SourceRecord.version.desc()).first()
    if srec and job.stored:
        db.add(m.Document(project_id=ctx.pid, record_id=srec.id, filename=name, mime_type=file.content_type or "", byte_size=len(data),
                          version=srec.version, uploaded_by=ctx.user.id))
    audit(db, "file_uploaded", ctx.user, ctx.org_id, ctx.pid, "record", srec.id if srec else None, filename=name)
    db.commit()
    return {**_job_dict(job), "record_id": srec.id if srec and job.stored else None, "filename": name}


def _rec_dict(r, with_content=False):
    d = {"id": r.id, "source_type": r.source_type, "record_type": r.record_type, "title": r.title, "author": r.author, "url": r.url,
         "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None, "visibility": r.visibility, "redactions": r.redactions,
         "injection_suspected": r.injection_suspected, "status": r.processing_status, "version": r.version}
    if with_content:
        d["content"] = r.content
    return d


@router.get("/projects/{project_id}/records")
def records(limit: int = 100, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    rows = db.query(m.SourceRecord).filter_by(project_id=ctx.pid).order_by(m.SourceRecord.ingested_at.desc()).limit(min(limit, 500)).all()
    return [_rec_dict(r) for r in rows if access.visible_record(r, ctx.org_role)]


@router.get("/projects/{project_id}/records/{record_id}")
def record(record_id: str, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    r = db.get(m.SourceRecord, record_id)
    if not r or r.project_id != ctx.pid or not access.visible_record(r, ctx.org_role):
        raise HTTPException(404, "Not found")
    return _rec_dict(r, True)


def _purge(db, ctx, r):
    removed_claims = 0
    for ev in db.query(m.EvidenceLink).filter_by(record_id=r.id).all():
        cid = ev.claim_id
        db.delete(ev)
        db.flush()
        c = db.get(m.Claim, cid)
        if c and not db.query(m.EvidenceLink).filter_by(claim_id=cid).count() and c.status != "verified":
            db.delete(c)
            removed_claims += 1
    db.query(m.DocumentChunk).filter_by(record_id=r.id).delete()
    db.query(m.Document).filter_by(record_id=r.id).delete()
    ledger.append(db, ctx.pid, "record_deleted", "record", r.id, actor=ctx.user.id, new_state={"claims_removed": removed_claims}, verification="verified")
    db.delete(r)
    db.flush()
    return removed_claims


@router.delete("/projects/{project_id}/records/{record_id}")
def delete_record(record_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    r = db.get(m.SourceRecord, record_id)
    if not r or r.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    removed = _purge(db, ctx, r)
    claims_engine.reconcile(db, ctx.pid)
    graph.rebuild_graph(db, ctx.pid)
    audit(db, "record_deleted", ctx.user, ctx.org_id, ctx.pid, "record", record_id)
    db.commit()
    return {"ok": True, "claims_removed": removed}


@router.delete("/projects/{project_id}/sources/{source_id}/records")
def delete_source_records(source_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    """Deletion request / consent withdrawal: removes everything previously ingested from one source."""
    s = _source(db, ctx, source_id)
    recs = db.query(m.SourceRecord).filter_by(project_id=ctx.pid, source_id=s.id).all()
    removed = sum(_purge(db, ctx, r) for r in recs)
    claims_engine.reconcile(db, ctx.pid)
    graph.rebuild_graph(db, ctx.pid)
    audit(db, "source_records_deleted", ctx.user, ctx.org_id, ctx.pid, "source", s.id, records=len(recs))
    db.commit()
    return {"ok": True, "records_deleted": len(recs), "claims_removed": removed}


@router.get("/projects/{project_id}/consents")
def consents(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return [{"author": c.author, "granted": c.granted} for c in db.query(m.ContributorConsent).filter_by(project_id=ctx.pid)]


@router.put("/projects/{project_id}/consents")
def set_consent(body: dict, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    """Record an individual's consent decision. Withdrawing removes their already-ingested contributions."""
    author = str(body.get("author", "")).strip()[:200]
    if not author:
        raise HTTPException(422, "author required")
    granted = bool(body.get("granted", False))
    c = db.query(m.ContributorConsent).filter_by(project_id=ctx.pid, author=author).first()
    if not c:
        c = m.ContributorConsent(project_id=ctx.pid, author=author)
        db.add(c)
    c.granted, c.decided_by = granted, ctx.user.id
    removed = 0
    if not granted:
        for r in db.query(m.SourceRecord).filter(m.SourceRecord.project_id == ctx.pid).all():
            if (r.author or "").lower() == author.lower():
                _purge(db, ctx, r)
                removed += 1
        claims_engine.reconcile(db, ctx.pid)
        graph.rebuild_graph(db, ctx.pid)
    ledger.append(db, ctx.pid, "consent_changed", "person", author, actor=ctx.user.id, new_state={"granted": granted, "records_removed": removed}, verification="verified")
    audit(db, "consent_changed", ctx.user, ctx.org_id, ctx.pid, "person", author, granted=granted)
    db.commit()
    return {"author": author, "granted": granted, "records_removed": removed}
