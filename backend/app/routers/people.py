from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..security import audit, need
from ..services import handover, interview

router = APIRouter(prefix="/api/projects/{project_id}", tags=["people"])


def _iv(db, ctx, iid):
    iv = db.get(m.HandoverInterview, iid)
    if not iv or iv.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    return iv


def _q(db, iv, qid):
    q = db.get(m.InterviewQuestion, qid)
    if not q or q.interview_id != iv.id:
        raise HTTPException(404, "Not found")
    return q


def _iv_dict(db, iv):
    qs = db.query(m.InterviewQuestion).filter_by(interview_id=iv.id).order_by(m.InterviewQuestion.position, m.InterviewQuestion.parent_question_id.isnot(None)).all()
    out = []
    for q in qs:
        rs = db.query(m.InterviewResponse).filter_by(question_id=q.id).all()
        out.append({"id": q.id, "parent_question_id": q.parent_question_id, "question": q.question, "context": q.context, "status": q.status,
                    "responses": [{"id": r.id, "answer": r.answer, "employee_confirmed": r.employee_confirmed, "manager_approved": r.manager_approved,
                                   "claim_id": r.claim_id} for r in rs]})
    return {"id": iv.id, "person": iv.person_key, "status": iv.status, "progress": interview.progress(db, iv), "questions": out}


@router.get("/interviews")
def interviews(ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    rows = db.query(m.HandoverInterview).filter_by(project_id=ctx.pid).all()
    mgr = ctx.org_role in ("manager", "admin")
    return [{"id": i.id, "person": i.person_key, "status": i.status, "progress": interview.progress(db, i)} for i in rows
            if mgr or i.person_user_id == ctx.user.id]


@router.post("/interviews", status_code=201)
def start_interview(body: dict, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    iv = interview.create(db, ctx.project, str(body.get("person", "")), ctx.user)
    audit(db, "interview_started", ctx.user, ctx.org_id, ctx.pid, "interview", iv.id)
    db.commit()
    return _iv_dict(db, iv)


@router.get("/interviews/{interview_id}")
def get_interview(interview_id: str, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    iv = _iv(db, ctx, interview_id)
    if ctx.org_role not in ("manager", "admin") and iv.person_user_id != ctx.user.id:
        raise HTTPException(404, "Not found")
    return _iv_dict(db, iv)


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


@router.post("/interviews/{interview_id}/questions/{question_id}/answers", status_code=201)
def answer(interview_id: str, question_id: str, body: AnswerIn, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    iv = _iv(db, ctx, interview_id)
    if iv.person_user_id != ctx.user.id:
        raise HTTPException(403, "Only the interviewed person can answer")
    q = _q(db, iv, question_id)
    resp, fq = interview.respond(db, ctx.project, iv, q, body.answer, ctx.user)
    db.commit()
    return {"response_id": resp.id, "follow_up": {"id": fq.id, "question": fq.question} if fq else None, "progress": interview.progress(db, iv)}


@router.post("/interviews/{interview_id}/responses/{response_id}/confirm")
def confirm(interview_id: str, response_id: str, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    iv = _iv(db, ctx, interview_id)
    resp = db.get(m.InterviewResponse, response_id)
    if not resp:
        raise HTTPException(404, "Not found")
    ap = interview.confirm(db, ctx.project, iv, resp, ctx.user)
    db.commit()
    return {"approval_id": ap.id}


@router.post("/interviews/{interview_id}/complete")
def complete(interview_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    iv = _iv(db, ctx, interview_id)
    iv.status = "completed"
    db.commit()
    return {"ok": True}


def _ap(a):
    return {"id": a.id, "kind": a.kind, "status": a.status, "target_id": a.target_id, "payload": {k: v for k, v in (a.payload or {}).items() if k != "answerer_user_id"},
            "requested_by": a.requested_by, "decided_by": a.decided_by, "note": a.note, "created_at": a.created_at.isoformat()}


@router.get("/approvals")
def approvals(status: str = "pending", ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    return [_ap(a) for a in db.query(m.Approval).filter_by(project_id=ctx.pid, status=status).order_by(m.Approval.created_at.desc())]


class DecideIn(BaseModel):
    approve: bool
    note: str = Field(default="", max_length=500)


@router.post("/approvals/{approval_id}/decide")
def decide(approval_id: str, body: DecideIn, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    ap = db.get(m.Approval, approval_id)
    if not ap or ap.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    interview.decide(db, ctx.project, ap, body.approve, ctx.user, body.note)
    audit(db, "approval_decided", ctx.user, ctx.org_id, ctx.pid, "approval", ap.id, approve=body.approve)
    db.commit()
    return _ap(ap)


@router.post("/scope-changes", status_code=201)
def scope_change(body: dict, ctx=Depends(need("contributor")), db: Session = Depends(get_db)):
    sel = db.get(m.SourceSelection, body.get("selection_id"))
    if not sel or sel.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    ap = m.Approval(project_id=ctx.pid, kind="scope_change", target_id=sel.id, status="pending", requested_by=ctx.user.id,
                    payload={"selection_id": sel.id, "included": bool(body.get("included", True)), "reason": str(body.get("reason", ""))[:500]})
    db.add(ap)
    db.commit()
    return {"approval_id": ap.id}


@router.post("/handovers", status_code=201)
def gen_handover(body: dict, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    inc = body.get("incoming_user_id")
    if inc and not db.query(m.Membership).filter_by(org_id=ctx.org_id, user_id=inc).first():
        raise HTTPException(404, "Incoming user not found")
    h = handover.generate(db, ctx.project, str(body.get("person", "")), ctx.user, ctx.org_role, inc, str(body.get("role_profile", ""))[:200])
    audit(db, "handover_generated", ctx.user, ctx.org_id, ctx.pid, "handover", h.id)
    db.commit()
    return handover.to_dict(db, h)


def _h(db, ctx, hid):
    h = db.get(m.Handover, hid)
    if not h or h.project_id != ctx.pid:
        raise HTTPException(404, "Not found")
    if ctx.org_role not in ("manager", "admin") and not (h.incoming_user_id == ctx.user.id and h.summary.get("status") == "approved"):
        raise HTTPException(404, "Not found")
    return h


@router.get("/handovers")
def handovers(ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    out = []
    for h in db.query(m.Handover).filter_by(project_id=ctx.pid).order_by(m.Handover.created_at.desc()):
        try:
            _h(db, ctx, h.id)
            out.append(handover.to_dict(db, h, False))
        except HTTPException:
            pass
    return out


@router.get("/handovers/{handover_id}")
def get_handover(handover_id: str, ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    return handover.to_dict(db, _h(db, ctx, handover_id))


@router.post("/handovers/{handover_id}/request-approval", status_code=201)
def req_approval(handover_id: str, ctx=Depends(need("manager")), db: Session = Depends(get_db)):
    h = _h(db, ctx, handover_id)
    ap = handover.request_approval(db, ctx.project, h, ctx.user)
    db.commit()
    return {"approval_id": ap.id}


@router.get("/handovers/{handover_id}/pdf")
def get_pdf(handover_id: str, ctx=Depends(need("incoming")), db: Session = Depends(get_db)):
    h = _h(db, ctx, handover_id)
    data = handover.pdf(db, h, ctx.project.name)
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="handover-{h.departing_person_key}.pdf"'})
