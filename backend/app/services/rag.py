"""Permission-filtered, cited Q&A. Order: permission filter -> retrieve -> answer from evidence -> or honest "not documented"."""
from .. import models as m
from . import access, ledger
from .embed import cosine, embed, overlap
from .extract import sentences
from . import llm

NO_ANSWER = "I don't have verified knowledge about that in the sources you can access. It has been added to the interview queue."
THRESHOLD = 0.5


def ask(db, project, user, role, question, log_gap=True):
    q = (question or "").strip()[:500]
    qv = embed(q)
    recs = {r.id: r for r in db.query(m.SourceRecord).filter_by(project_id=project.id)
            if access.visible_record(r, role) and not r.injection_suspected}
    scored = []
    for ch in db.query(m.DocumentChunk).filter_by(project_id=project.id):
        if ch.record_id not in recs:
            continue
        s = 0.5 * cosine(qv, ch.embedding) + 0.5 * overlap(q, ch.text)
        if s >= 0.15:
            scored.append((s, ch))
    scored.sort(key=lambda x: -x[0])
    cands = []  # (score, citation, text)
    for c in access.visible_claims(db, project.id, role):
        if c.status in ("missing", "superseded") or c.details.get("draft"):
            continue
        sc = overlap(q, c.statement + " " + " ".join(str(v) for v in c.details.values() if isinstance(v, str)))
        if c.category in ("component", "contribution"):
            sc *= 0.4
        if sc < THRESHOLD:
            continue
        for ev in db.query(m.EvidenceLink).filter_by(claim_id=c.id).limit(1):
            if ev.record_id and ev.record_id not in recs:
                continue
            rec = recs.get(ev.record_id)
            cands.append((sc + 0.05, {"claim_id": c.id, "status": c.status, "source": rec.title if rec else "Interview answer",
                                      "location": ev.location, "quote": ev.excerpt, "record_id": ev.record_id},
                          f"{c.statement} ({c.status.replace('_', ' ')})"))
    for s_, ch in scored[:5]:
        rec = recs[ch.record_id]
        for sent in sentences(ch.text):
            sc = overlap(q, sent)
            if sc >= THRESHOLD:
                cands.append((sc, {"claim_id": None, "status": "source_text", "source": rec.title, "location": f"chunk {ch.position + 1}",
                                   "quote": sent[:300], "record_id": rec.id}, sent[:300]))
    cands.sort(key=lambda x: -x[0])
    citations, parts, seen = [], [], set()
    for sc, cit, txt in cands:
        k = txt.lower()[:60]
        if k in seen:
            continue
        seen.add(k)
        citations.append(cit)
        parts.append(txt)
        if len(citations) == 3:
            break
    if not citations:
        if log_gap:
            _log_gap(db, project, user, q)
        return {"answer": NO_ANSWER, "citations": [], "answered": False}
    text = " ".join(parts)
    llm_text = llm.rephrase(q, [c["quote"] for c in citations]) if llm.available() else None
    return {"answer": llm_text or text, "citations": citations, "answered": True, "llm_used": bool(llm_text)}


def _log_gap(db, project, user, q):
    key = "question:" + q.lower()[:80]
    if not db.query(m.KnowledgeGap).filter_by(project_id=project.id, gap_type="unanswered_question", entity_key=key).first():
        db.add(m.KnowledgeGap(project_id=project.id, gap_type="unanswered_question", entity_type="question", entity_key=key,
                              description=f"Question could not be answered: {q[:150]}", found="No accessible evidence matched.",
                              recommended_action="Ask the relevant owner and record the answer."))
    if not db.query(m.Claim).filter_by(project_id=project.id, subject_key=key, status="missing").first():
        c = m.Claim(project_id=project.id, category="question_missing", subject_key=key, statement=q[:300], details={"question": q}, status="missing",
                    created_by="system:missing")
        db.add(c)
        db.flush()
        ledger.append(db, project.id, "knowledge_missing", "claim", c.id, actor=getattr(user, "id", None), new_state={"status": "missing"}, verification="missing")
