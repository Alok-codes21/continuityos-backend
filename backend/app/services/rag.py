"""Permission-filtered, cited Q&A. Order: permission filter -> retrieve -> answer from evidence -> or honest "not documented"."""
from .. import models as m
from . import access, ledger
from .embed import cosine, embed, overlap
from .extract import sentences
from . import llm

NO_ANSWER = "I don't have verified knowledge about that in the sources you can access. It has been recorded as a knowledge gap."
THRESHOLD = 0.5


def ask(db, project, user, role, question, log_gap=True):
    q = (question or "").strip()[:500]
    qv = embed(q)
    recs = {r.id: r for r in db.query(m.SourceRecord).filter_by(project_id=project.id)
            if access.visible_record(r, role) and not r.injection_suspected}
    # Superseded source snapshots remain auditable, not current answer evidence.
    newest = {}
    for record in db.query(m.SourceRecord).filter_by(project_id=project.id):
        key = (record.source_id, record.source_type, record.external_id)
        if key not in newest or record.version > newest[key].version:
            newest[key] = record
    current_ids = {record.id for record in newest.values()}
    recs = {key: value for key, value in recs.items() if key in current_ids}
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
        if c.status in ("missing", "superseded", "conflicting", "outdated") or c.freshness == "stale" or c.details.get("draft"):
            continue
        if c.details.get("verification_method") == "approved_correction":
            # Original source excerpts support the old statement, not the edit.
            # Corrections remain visible for human review but are not RAG proof.
            continue
        if c.details.get("needs_reverification"):
            continue
        sc = overlap(q, c.statement + " " + " ".join(str(v) for v in c.details.values() if isinstance(v, str)))
        if c.category in ("component", "contribution"):
            sc *= 0.4
        if sc < THRESHOLD:
            continue
        for ev in db.query(m.EvidenceLink).filter_by(claim_id=c.id).all():
            if ev.record_id and ev.record_id not in recs:
                continue  # this evidence is restricted/flagged for this role; try the claim's other evidence
            rec = recs.get(ev.record_id)
            cands.append((sc + 0.05, {"claim_id": c.id, "status": c.status, "source": rec.title if rec else "Interview answer",
                                      "location": ev.location, "quote": ev.excerpt, "record_id": ev.record_id},
                          f"{c.statement} ({c.status.replace('_', ' ')})"))
            break
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
            _log_gap(db, project, user, q, role)
        return {"answer": NO_ANSWER, "citations": [], "answered": False}
    text = " ".join(parts)
    llm_text = llm.rephrase(q, [c["quote"] for c in citations]) if llm.available() else None
    if llm_text and not _supported(llm_text, citations):
        llm_text = None  # every sentence must be backed by the cited excerpts, otherwise the plain cited text is returned
    return {"answer": llm_text or text, "citations": citations, "answered": True, "llm_used": bool(llm_text)}


def _supported(answer, citations):
    """Every sentence must cite an excerpt [n], and be backed by THAT excerpt: most of its words, and all its numbers, appear in it."""
    import re
    for sent in re.split(r"(?<=[.!?])\s+", answer.strip()):
        marks = [int(x) for x in re.findall(r"\[(\d+)\]", sent)]
        if not marks or any(k < 1 or k > len(citations) for k in marks):
            return False
        body = re.sub(r"\[\d+\]", "", sent)
        ev_text = " ".join(citations[k - 1]["quote"] for k in marks)
        ev = set(re.findall(r"[a-z0-9]{3,}", ev_text.lower()))
        words = set(re.findall(r"[a-z0-9]{3,}", body.lower()))
        neg = {"not", "no", "never", "without", "cannot"}
        if (words & neg) != (ev & neg):
            return False
        if words and len(words & ev) / len(words) < 0.6:
            return False
        if set(re.findall(r"\b\d+\b", body)) - set(re.findall(r"\b\d+\b", ev_text)):
            return False
        if llm.available():
            # with a model configured, a sentence must be positively entailed; unclear or error means unsupported
            if llm.entails(ev_text, body) is not True:
                return False
        elif words and len(words & ev) / len(words) < 0.75:
            # without a model, the lexical bar is higher
            return False
    return True


def _log_gap(db, project, user, q, role):
    key = "question:" + q.lower()[:80]
    if not db.query(m.KnowledgeGap).filter_by(project_id=project.id, gap_type="unanswered_question", entity_key=key).first():
        db.add(m.KnowledgeGap(project_id=project.id, gap_type="unanswered_question", entity_type="question", entity_key=key,
                              description=f"Question could not be answered: {q[:150]}", found="No accessible evidence matched.",
                              recommended_action="Ask the relevant owner and record the answer."))
    if not db.query(m.Claim).filter_by(project_id=project.id, subject_key=key, status="missing").first():
        c = m.Claim(project_id=project.id, category="question_missing", subject_key=key, statement=q[:300], details={"question": q, "asker_role": role}, status="missing",
                    created_by="system:missing")
        db.add(c)
        db.flush()
        ledger.append(db, project.id, "knowledge_missing", "claim", c.id, actor=getattr(user, "id", None), new_state={"status": "missing"}, verification="missing")
