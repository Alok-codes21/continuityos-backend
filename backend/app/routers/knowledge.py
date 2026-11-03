from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..security import audit, need
from ..services import access, claims_engine, graph, ledger, rag, risk

router = APIRouter(prefix="/api/projects/{project_id}", tags=["knowledge"])
STATES = ["verified", "evidence_backed", "inferred", "conflicting", "outdated", "missing", "superseded"]
WEIGHTS = {"verified": 1.0, "evidence_backed": 0.7, "inferred": 0.3}


def claim_dict(db, c, role, full=False):
    d = {"id": c.id, "category": c.category, "subject_key": c.subject_key, "statement": c.statement, "status": c.status,
         "freshness": c.freshness, "draft": bool(c.details.get("draft")), "superseded_by": c.superseded_by,
         "updated_at": c.updated_at.isoformat() if c.updated_at else None}
    if full:
        d["details"] = {k: v for k, v in c.details.items() if k not in ("answer",)}
        ev = []
        for e in db.query(m.EvidenceLink).filter_by(claim_id=c.id):
            r = db.get(m.SourceRecord, e.record_id) if e.record_id else None
            if r and not access.visible_record(r, role):
                continue
            ev.append({"id": e.id, "source": r.title if r else "Interview answer", "source_type": r.source_type if r else "interview",
                       "record_id": e.record_id, "location": e.location, "quote": e.excerpt, "quote_verified": e.quote_verified,
                       "url": r.url if r else None})
        d["evidence"] = ev
    return d


@router.get("/overview")
def overview(ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    claims = access.visible_claims(db, ctx.pid, ctx.org_role)
    counts = Counter(c.status for c in claims if not c.details.get("draft"))
    live = sum(v for k, v in counts.items() if k not in ("superseded",))
    score = round(100 * sum(WEIGHTS.get(k, 0) * v for k, v in counts.items()) / live) if live else 0
    ok_claims = {c.id for c in access.visible_claims(db, ctx.pid, ctx.org_role)}
    decisions = [d for d in db.query(m.Decision).filter_by(project_id=ctx.pid).order_by(m.Decision.decided_at.desc())
                 if not d.claim_id or d.claim_id in ok_claims][:5]
    today = m.now().date()
    days = {(today - timedelta(days=i)): 0 for i in range(13, -1, -1)}
    for r in db.query(m.SourceRecord).filter(m.SourceRecord.project_id == ctx.pid, m.SourceRecord.ingested_at >= m.now() - timedelta(days=14)):
        if access.visible_record(r, ctx.org_role) and r.ingested_at.date() in days:
            days[r.ingested_at.date()] += 1
    rk = risk.people_overview(db, ctx.pid) if ctx.org_role in ("manager", "admin") else []
    return {"health_score": score,
            "health_formula": "100 x (1.0*verified + 0.7*evidence_backed + 0.3*inferred) / all live claims; missing, conflicting and outdated count as 0",
            "state_counts": {s: counts.get(s, 0) for s in STATES},
            "open_gaps": db.query(m.KnowledgeGap).filter_by(project_id=ctx.pid, status="open").count() if ctx.org_role in ("manager", "admin") else None,
            "risks": rk[:5],
            "latest_decisions": [{"id": d.id, "title": d.title, "decided_by": d.decided_by, "at": d.decided_at.isoformat() if d.decided_at else None} for d in decisions],
            "ingestion_14d": [{"date": k.isoformat(), "records": v} for k, v in days.items()],
            "ledger": ledger.verify_chain(db, ctx.pid)}


@router.get("/claims")
def claims(status: str | None = None, category: str | None = None, q: str | None = None, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    rows = access.visible_claims(db, ctx.pid, ctx.org_role, [status] if status else None)
    out = [claim_dict(db, c, ctx.org_role) for c in rows if (not category or c.category == category) and (not q or q.lower() in c.statement.lower())
           and not c.details.get("draft")]
    return out[:500]


@router.get("/claims/{claim_id}")
def claim(claim_id: str, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    c = db.get(m.Claim, claim_id)
    if not c or c.project_id != ctx.pid or not access.can_see_level(ctx.org_role, access.claim_level(db, c)):
        raise HTTPException(404, "Not found")
    d = claim_dict(db, c, ctx.org_role, True)
    d["history"] = [{"seq": e.seq, "type": e.event_type, "at": e.occurred_at.isoformat(), "verification": e.verification}
                    for e in db.query(m.KnowledgeEvent).filter_by(project_id=ctx.pid, entity_type="claim", entity_id=c.id).order_by(m.KnowledgeEvent.seq)]
    return d


class CorrectionIn(BaseModel):
    corrected_statement: str = Field(min_length=3, max_length=1000)
    reason: str = Field(default="", max_length=500)


@router.post("/claims/{claim_id}/corrections", status_code=201)
def correct(claim_id: str, body: CorrectionIn, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    c = db.get(m.Claim, claim_id)
    if not c or c.project_id != ctx.pid or not access.can_see_level(ctx.org_role, access.claim_level(db, c)):
        raise HTTPException(404, "Not found")
    ap = m.Approval(project_id=ctx.pid, kind="member_correction", target_id=c.id, status="pending", requested_by=ctx.user.id,
                    payload={"claim_id": c.id, "corrected_statement": body.corrected_statement, "reason": body.reason, "original": c.statement})
    db.add(ap)
    db.commit()
    return {"approval_id": ap.id}


@router.get("/ledger")
def ledger_list(limit: int = 100, before_seq: int | None = None, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    q = db.query(m.KnowledgeEvent).filter_by(project_id=ctx.pid)
    if before_seq:
        q = q.filter(m.KnowledgeEvent.seq < before_seq)
    out = []
    for e in q.order_by(m.KnowledgeEvent.seq.desc()).limit(min(limit, 500)):
        if not access.can_see_level(ctx.org_role, e.permission or "restricted"):
            continue
        out.append({"seq": e.seq, "type": e.event_type, "entity_type": e.entity_type, "entity_id": e.entity_id, "actor": e.actor,
                    "verification": e.verification, "at": e.occurred_at.isoformat(), "hash": e.hash[:16], "previous_state": e.previous_state,
                    "new_state": e.new_state})
    return out


@router.get("/ledger/verify")
def ledger_verify(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return ledger.verify_chain(db, ctx.pid)


@router.get("/graph")
def graph_view(ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    restricted_claims = {c.id for c in db.query(m.Claim).filter_by(project_id=ctx.pid) if not access.can_see_level(ctx.org_role, access.claim_level(db, c))}
    edges = [e for e in db.query(m.GraphEdge).filter_by(project_id=ctx.pid) if e.claim_id not in restricted_claims]
    used = {e.src_id for e in edges} | {e.dst_id for e in edges}
    seen_keys = set()
    for c in access.visible_claims(db, ctx.pid, ctx.org_role):
        for k in ("component", "from", "to"):
            if isinstance(c.details.get(k), str):
                seen_keys.add(c.details[k])
    nodes = [n for n in db.query(m.GraphNode).filter_by(project_id=ctx.pid)
             if n.id in used or (n.node_type in ("service", "module") and n.key in seen_keys)]
    return {"nodes": [{"id": n.id, "type": n.node_type, "key": n.key, "name": n.name, "user_id": n.user_id} for n in nodes],
            "edges": [{"id": e.id, "source": e.src_id, "target": e.dst_id, "relation": e.relation, "verification": e.verification, "claim_id": e.claim_id} for e in edges]}


@router.get("/graph/people")
def people(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return [{"key": p.key, "name": p.name, "user_id": p.user_id, "aliases": p.props.get("display_aliases", [])}
            for p in db.query(m.GraphNode).filter_by(project_id=ctx.pid, node_type="person")]


@router.post("/graph/people/merge")
def merge(body: dict, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    keep = graph.merge_people(db, ctx.pid, str(body.get("keep", "")), str(body.get("merge", "")))
    if not keep:
        raise HTTPException(404, "People not found")
    ledger.append(db, ctx.pid, "identity_merged", "person", keep.key, actor=ctx.user.id, new_state={"merged": body.get("merge")}, verification="verified")
    graph.rebuild_graph(db, ctx.pid)
    audit(db, "identity_merged", ctx.user, ctx.org_id, ctx.pid)
    db.commit()
    return {"ok": True}


@router.get("/gaps")
def gaps(status: str = "open", ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return [{"id": g.id, "type": g.gap_type, "entity": g.entity_key, "description": g.description, "found": g.found,
             "recommended_action": g.recommended_action, "status": g.status} for g in db.query(m.KnowledgeGap).filter_by(project_id=ctx.pid, status=status)]


@router.post("/analyse")
def reanalyse(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    claims_engine.reconcile(db, ctx.pid)
    graph.rebuild_graph(db, ctx.pid)
    r = claims_engine.rebuild_gaps(db, ctx.pid)
    db.commit()
    return r


@router.get("/risk/bus-factor")
def bus(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return risk.bus_factor(db, ctx.pid)


@router.get("/risk/people")
def risk_people(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return risk.people_overview(db, ctx.pid)


@router.post("/simulations")
def simulate(body: dict, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    r = risk.simulate(db, ctx.pid, str(body.get("person", "")), user=ctx.user)
    if r is None:
        raise HTTPException(404, "Person not found")
    db.commit()
    return r


@router.get("/simulations")
def sim_history(ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return [{"id": r.id, "person": r.simulation_person_key, "title": r.title, "level": r.level, "at": r.created_at.isoformat()}
            for r in db.query(m.RiskRecord).filter_by(project_id=ctx.pid).order_by(m.RiskRecord.created_at.desc()).limit(50)]


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@router.post("/ask")
def ask(body: AskIn, ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    r = rag.ask(db, ctx.project, ctx.user, ctx.org_role, body.question)
    audit(db, "ai_retrieval", ctx.user, ctx.org_id, ctx.pid, answered=r["answered"], citations=len(r["citations"]),
          record_ids=sorted({c["record_id"] for c in r["citations"] if c.get("record_id")}), claim_ids=sorted({c["claim_id"] for c in r["citations"] if c.get("claim_id")}))
    ledger.append(db, ctx.pid, "ai_retrieval", "question", ctx.user.id, actor=ctx.user.id, new_state={"answered": r["answered"], "records": len(r["citations"])}, verification="verified")
    db.commit()
    return r


@router.post("/rehearsal", status_code=201)
def rehearsal_start(ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    s = m.RehearsalSession(project_id=ctx.pid, user_id=ctx.user.id, turns=[])
    db.add(s)
    db.commit()
    return {"id": s.id}


@router.post("/rehearsal/{session_id}/ask")
def rehearsal_ask(session_id: str, body: AskIn, ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    s = db.get(m.RehearsalSession, session_id)
    if not s or s.project_id != ctx.pid or s.user_id != ctx.user.id:
        raise HTTPException(404, "Not found")
    r = rag.ask(db, ctx.project, ctx.user, ctx.org_role, body.question)
    s.turns = [*s.turns, {"q": body.question, "answered": r["answered"], "answer": r["answer"], "citations": r["citations"]}]
    db.commit()
    answered = sum(1 for t in s.turns if t["answered"])
    return {**r, "turns": len(s.turns), "answered_turns": answered}


@router.get("/rehearsal/{session_id}")
def rehearsal_get(session_id: str, ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    s = db.get(m.RehearsalSession, session_id)
    if not s or s.project_id != ctx.pid or s.user_id != ctx.user.id:
        raise HTTPException(404, "Not found")
    return {"id": s.id, "turns": s.turns}


@router.get("/skills")
def skills(ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    return [{"id": s.id, "user_id": s.user_id, "skill": s.skill, "level": s.level, "source": s.source, "approved": s.approved}
            for s in db.query(m.PeopleKnowledge).filter_by(project_id=ctx.pid) if s.approved or ctx.org_role in ("manager", "admin") or s.user_id == ctx.user.id]


@router.post("/skills", status_code=201)
def add_skill(body: dict, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    name = str(body.get("skill", "")).strip()[:100]
    if not name:
        raise HTTPException(422, "Skill required")
    mgr = ctx.org_role in ("manager", "admin")
    uid_ = body.get("user_id") if mgr and body.get("user_id") else ctx.user.id
    s = m.PeopleKnowledge(project_id=ctx.pid, user_id=uid_, skill=name, level=str(body.get("level", "working"))[:20], source="self_declared", approved=False)
    db.add(s)
    db.commit()
    return {"id": s.id, "approved": False}


@router.post("/skills/{skill_id}/approve")
def approve_skill(skill_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    s = db.get(m.PeopleKnowledge, skill_id)
    if not s or s.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    if s.user_id == ctx.user.id:
        raise HTTPException(403, "You cannot approve your own skill")
    s.approved = True
    ledger.append(db, ctx.pid, "skill_approved", "skill", s.id, actor=ctx.user.id, verification="verified")
    db.commit()
    return {"ok": True}
