"""AI Handover Interview: questions are generated from real gaps; answers become Draft claims that need the employee's
confirmation and a manager's approval (never the answerer) before they turn Verified."""
import re

from fastapi import HTTPException

from .. import models as m
from . import llm, claims_engine, graph, ledger
from .extract import NUMWORDS, comp_base, person_key

DETAIL_MIN_WORDS = 4


def _person_scope(db, pid, person):
    """Component keys and decision keys that relate to the departing person."""
    comps, decs = set(), set()
    for e in db.query(m.GraphEdge).filter_by(project_id=pid).all():
        if e.src_id == person.id:
            dst = db.get(m.GraphNode, e.dst_id)
            if dst.node_type in ("service", "module"):
                comps.add(dst.key)
            elif dst.node_type == "decision":
                decs.add(dst.key)
    return comps, decs


def _gap_question(g):
    t = g.gap_type
    ent = g.entity_key or ""
    if t == "no_documented_owner":
        return f"Who owns {ent} today, and who could cover for them?"
    if t == "missing_procedure":
        return f"Please describe the {ent.split(':')[-1]} steps for {ent.split(':')[0]}. What do you run, in what order, and how do you know it worked?"
    if t == "undocumented_decision":
        return f"Why was this decided: \"{g.description.split(': ', 1)[-1]}\"? What alternatives were considered?"
    if t == "conflict":
        return f"Our sources disagree. {g.found} Which one is correct?"
    if t == "unresolved_bug":
        return f"What is the current status of: {g.description.split(': ', 1)[-1]} Is it fixed, who is on it, and what is left?"
    return g.description


def create(db, project, person_key_, created_by):
    p = graph.resolve_person(db, project.id, person_key_)
    if not p:
        raise HTTPException(404, "Person not found")
    claims_engine.rebuild_gaps(db, project.id)
    comps, decs = _person_scope(db, project.id, p)
    gaps = db.query(m.KnowledgeGap).filter_by(project_id=project.id, status="open").all()
    related = [g for g in gaps if (g.entity_key or "").split(":")[0] in comps or g.entity_key in decs
               or (g.gap_type == "conflict" and any(c in (g.entity_key or "") for c in comps))]
    iv = m.HandoverInterview(project_id=project.id, person_key=p.key, person_user_id=p.user_id, status="active", created_by=created_by.id)
    db.add(iv)
    db.flush()
    for i, g in enumerate(related):
        db.add(m.InterviewQuestion(interview_id=iv.id, gap_id=g.id, question=_gap_question(g),
                                   context={"found": g.found, "gap_type": g.gap_type, "entity": g.entity_key}, status="open", position=i))
    ledger.append(db, project.id, "interview_started", "interview", iv.id, actor=created_by.id, new_state={"person": p.key, "questions": len(related)})
    db.flush()
    return iv


def progress(db, iv):
    qs = db.query(m.InterviewQuestion).filter(m.InterviewQuestion.interview_id == iv.id, m.InterviewQuestion.parent_question_id.is_(None)).all()
    covered = 0
    for q in qs:
        if q.status == "answered":
            covered += 1
    return {"covered": covered, "total": len(qs)}


_TEENS = {"eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}


def _num_in(text):
    """Numbers mentioned in text, digits or words ('five', 'sixty', 'sixty five', 'two hundred')."""
    out = set(re.findall(r"\d+(?:\.\d+)?", text))
    words = re.findall(r"[a-z]+", text.lower())
    i = 0
    while i < len(words):
        w = words[i]
        val = None
        if w in NUMWORDS:
            val = NUMWORDS[w]
        elif w in _TEENS:
            val = _TEENS[w]
        elif w in _TENS:
            val = _TENS[w]
            if i + 1 < len(words) and words[i + 1] in NUMWORDS and NUMWORDS[words[i + 1]] < 10:
                val += NUMWORDS[words[i + 1]]
                i += 1
        if val is not None:
            if i + 1 < len(words) and words[i + 1] == "hundred":
                val *= 100
                i += 1
            out.add(str(val))
        i += 1
    return out


def _followup(db, iv, q, answer):
    g = db.get(m.KnowledgeGap, q.gap_id) if q.gap_id else None
    if not g or q.parent_question_id:
        return None
    gt, words = g.gap_type, len(answer.split())
    low = answer.lower()
    comp = (g.entity_key or "").split(":")[0]
    text = None
    if gt == "conflict":
        vals = _conflict_values(db, g)
        if not (_num_in(answer) & {str(v) for v in vals}) and not any(str(v).lower() in low for v in vals):
            text = f"Which exact value is correct: {', '.join(str(v) for v in vals)}? Please name one."
    elif gt == "missing_procedure":
        if words < DETAIL_MIN_WORDS:
            text = "Can you add a bit more detail so a new person could act on it? What are the concrete steps?"
        elif not re.search(r"\b(?:step|first|then|next|run|restart|check|deploy|rollback|verify|after)\b|\d\.|->", low):
            text = f"What are the steps for {comp}, in order, and how do you know each one worked?"
    elif gt == "undocumented_decision":
        if words < DETAIL_MIN_WORDS:
            text = "Can you add a bit more detail so a new person could act on it? What are the concrete reasons?"
        elif not re.search(r"\b(?:because|so that|due to|reason|trade-?off|instead|alternative|risk)\b", low):
            text = "What was the reason for this decision, and what other options were considered?"
    elif gt == "no_documented_owner":
        if words < 1:
            text = "Please name the owner."
        elif not re.search(r"\b(?:backup|deputy|alternate|second|cover|also knows)\b", low):
            text = f"Who could cover {comp} if the owner is away? Please name a backup."
    if text is None and llm.available():
        text = llm.followup(q.question, answer)
    if not text:
        return None
    fq = m.InterviewQuestion(interview_id=iv.id, gap_id=g.id, parent_question_id=q.id, question=text, context=q.context, status="open",
                             position=q.position)
    db.add(fq)
    db.flush()
    return fq


def _conflict_values(db, gap):
    cs = db.query(m.Claim).filter_by(project_id=gap.project_id, subject_key=gap.entity_key, category="config_value").all()
    return [c.details.get("value") for c in cs if c.status in ("conflicting", "evidence_backed", "inferred", "verified")]


def respond(db, project, iv, q, answer, user):
    if iv.status != "active":
        raise HTTPException(409, "Interview is not active")
    answer = (answer or "").strip()
    if not answer:
        raise HTTPException(422, "Empty answer")
    if q.interview_id != iv.id:
        raise HTTPException(404, "Not found")
    g = db.get(m.KnowledgeGap, q.gap_id) if q.gap_id else None
    resp = m.InterviewResponse(interview_id=iv.id, question_id=q.id, answer=answer[:4000])
    db.add(resp)
    db.flush()
    claim = None
    if g and g.gap_type != "conflict":
        claim = _draft_claim(db, project, iv, g, answer, resp)
        resp.claim_id = claim.id
    fq = _followup(db, iv, q, answer)
    q.status = "followup" if fq else "answered"
    ledger.append(db, project.id, "interview_answer_drafted", "interview_response", resp.id, actor=user.id,
                  new_state={"question": q.id, "gap": g.gap_type if g else None}, verification="inferred")
    db.flush()
    return resp, fq


def _draft_claim(db, project, iv, g, answer, resp):
    comp = (g.entity_key or "").split(":")[0]
    d = {"draft": True, "answer": answer, "interview": iv.id, "answered_by": iv.person_key, "gap_id": g.id}
    if g.gap_type == "no_documented_owner":
        owner = answer.split(",")[0].split(" and ")[0].strip().lstrip("@")[:80]
        d.update({"owner": owner, "component": comp})
        key, cat, text = f"owner:{comp}:{person_key(owner)}", "owner", f"{owner} owns {comp}"
    elif g.gap_type == "missing_procedure":
        topic = g.entity_key.split(":")[-1]
        d.update({"component": comp, "topic": topic})
        key, cat, text = f"procedure:{comp}:{topic}", "procedure", answer[:900]
    elif g.gap_type == "undocumented_decision":
        d.update({"decision": g.entity_key})
        key, cat, text = f"rationale:{g.entity_key}", "rationale", answer[:900]
    else:
        d.update({"target": g.entity_key})
        key, cat, text = f"status:{g.entity_key}", "status_note", answer[:900]
    c = m.Claim(project_id=project.id, category=cat, subject_key=key, statement=text, details=d, status="inferred", created_by=f"interview:{iv.id}")
    db.add(c)
    db.flush()
    db.add(m.EvidenceLink(claim_id=c.id, interview_response_id=resp.id, excerpt=answer[:500], location="interview answer", quote_verified=True))
    return c


def confirm(db, project, iv, resp, user):
    """Employee confirms their own answer; this creates the approval card for a manager."""
    if resp.interview_id != iv.id:
        raise HTTPException(404, "Not found")
    if iv.person_user_id != user.id:
        raise HTTPException(403, "Only the interviewed person can confirm their answers")
    resp.employee_confirmed = True
    ap = m.Approval(project_id=project.id, kind="interview_answer", target_id=resp.id, status="pending",
                    payload={"interview_id": iv.id, "question_id": resp.question_id, "answered_by": iv.person_key,
                             "answer": resp.answer, "answerer_user_id": user.id}, requested_by=user.id)
    db.add(ap)
    ledger.append(db, project.id, "interview_answer_confirmed", "interview_response", resp.id, actor=user.id, verification="inferred")
    db.flush()
    return ap


def _verify(db, project, claim, approver):
    prev = claim.status
    d = dict(claim.details)
    d.pop("draft", None)
    claim.details = d
    claim.status, claim.verified_by = "verified", approver.id
    ledger.append(db, project.id, "claim_verified", "claim", claim.id, actor=approver.id, previous_state={"status": prev},
                  new_state={"status": "verified"}, verification="verified")


def _apply_approved(db, project, resp, approver):
    q = db.get(m.InterviewQuestion, resp.question_id)
    iv = db.get(m.HandoverInterview, resp.interview_id)
    g = db.get(m.KnowledgeGap, q.gap_id) if q.gap_id else None
    resolved_comp = None
    if g and g.gap_type == "conflict":
        vals = {c.id: c for c in db.query(m.Claim).filter_by(project_id=project.id, subject_key=g.entity_key, category="config_value")
                if c.status in ("conflicting", "evidence_backed", "inferred", "verified")}
        nums = _num_in(resp.answer)
        chosen = [c for c in vals.values() if str(c.details.get("value")) in nums or str(c.details.get("value")).lower() in resp.answer.lower()]
        if len(chosen) != 1:
            raise HTTPException(409, "Answer does not pick exactly one value; ask a follow-up")
        win = chosen[0]
        _verify(db, project, win, approver)
        for c in vals.values():
            if c.id != win.id:
                c.status, c.superseded_by = "superseded", win.id
                ledger.append(db, project.id, "claim_superseded", "claim", c.id, actor=approver.id, new_state={"by": win.id}, verification="verified")
        resp.claim_id = win.id
        resolved_comp = g.entity_key.split(":")[1] if ":" in g.entity_key else None
    elif resp.claim_id:
        claim = db.get(m.Claim, resp.claim_id)
        missing = db.query(m.Claim).filter(m.Claim.project_id == project.id, m.Claim.subject_key == claim.subject_key,
                                           m.Claim.status == "missing").all()
        for mc in missing:
            db.delete(mc)
        db.flush()
        _verify(db, project, claim, approver)
        if claim.category == "bug" or g.gap_type == "unresolved_bug":
            pass
        resolved_comp = claim.details.get("component")
        if claim.category == "owner":
            claims_engine.upsert_component(db, project.id, claim.details["component"])
    if g and g.gap_type == "unresolved_bug" and re.search(r"(?i)\b(fixed|resolved|closed|done)\b", resp.answer):
        bug = db.query(m.Claim).filter_by(project_id=project.id, subject_key=g.entity_key).first()
        if bug:
            bug.details = {**bug.details, "resolved": True}
    # the answerer is a verified holder of the component they just documented
    if resolved_comp and db.query(m.Component).filter_by(project_id=project.id, key=comp_base(resolved_comp)).first():
        hk = f"holder:{comp_base(resolved_comp)}:{iv.person_key}"
        hc = db.query(m.Claim).filter_by(project_id=project.id, subject_key=hk).first()
        if not hc:
            name = (graph.resolve_person(db, project.id, iv.person_key) or type("x", (), {"name": iv.person_key})).name
            hc = m.Claim(project_id=project.id, category="holder", subject_key=hk, statement=f"{name} holds verified knowledge of {comp_base(resolved_comp)}",
                         details={"person": iv.person_key, "component": comp_base(resolved_comp), "via": "approved interview answer"},
                         status="verified", created_by=f"interview:{iv.id}", verified_by=approver.id)
            db.add(hc)
            db.flush()
            db.add(m.EvidenceLink(claim_id=hc.id, interview_response_id=resp.id, excerpt=resp.answer[:500], location="interview answer", quote_verified=True))
            ledger.append(db, project.id, "claim_verified", "claim", hc.id, actor=approver.id, new_state={"status": "verified"}, verification="verified")
    q.status = "answered"
    resp.manager_approved = True
    db.flush()
    claims_engine.rebuild_gaps(db, project.id)
    graph.rebuild_graph(db, project.id)


def decide(db, project, ap, approve, approver, note=""):
    if ap.project_id != project.id:
        raise HTTPException(404, "Not found")
    if ap.status != "pending":
        raise HTTPException(409, "Already decided")
    if approver.id == ap.requested_by or approver.id == (ap.payload or {}).get("answerer_user_id"):
        raise HTTPException(403, "You cannot approve your own request")
    if approve:
        if ap.kind == "interview_answer":
            resp = db.get(m.InterviewResponse, ap.target_id)
            if not resp.employee_confirmed:
                raise HTTPException(409, "The employee has not confirmed this answer")
            _apply_approved(db, project, resp, approver)
        elif ap.kind == "handover_doc":
            from . import handover
            handover.approve(db, project, ap, approver)
        elif ap.kind == "member_correction":
            _apply_correction(db, project, ap, approver)
        elif ap.kind == "scope_change":
            _apply_scope(db, project, ap, approver)
        else:
            raise HTTPException(422, "Unknown approval kind")
    ap.status = "approved" if approve else "rejected"
    ap.decided_by, ap.note, ap.decided_at = approver.id, note[:500], m.now()
    ledger.append(db, project.id, f"approval_{ap.status}", "approval", ap.id, actor=approver.id, new_state={"kind": ap.kind},
                  verification="verified" if approve else "inferred")
    db.flush()
    return ap


def _apply_correction(db, project, ap, approver):
    c = db.get(m.Claim, ap.payload.get("claim_id"))
    if not c or c.project_id != project.id:
        raise HTTPException(404, "Claim not found")
    prev = c.status
    c.statement = ap.payload["corrected_statement"][:1000]
    c.status, c.verified_by = "verified", approver.id
    ledger.append(db, project.id, "claim_corrected", "claim", c.id, actor=approver.id, previous_state={"status": prev}, new_state={"status": "verified"}, verification="verified")
    graph.rebuild_graph(db, project.id)


def _apply_scope(db, project, ap, approver):
    pl = ap.payload
    sel = db.get(m.SourceSelection, pl.get("selection_id"))
    if not sel or sel.project_id != project.id:
        raise HTTPException(404, "Selection not found")
    sel.included = bool(pl.get("included", True))
    ledger.append(db, project.id, "scope_changed", "selection", sel.id, actor=approver.id, new_state={"included": sel.included}, verification="verified")
