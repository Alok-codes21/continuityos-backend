"""Scenario-based rehearsal: questions are built from the project's real knowledge, then each one is answered through the
permission-filtered RAG. Readiness = how many scenarios the incoming person's workspace can answer with evidence."""
from .. import models as m
from . import access, rag


def scenarios(db, project, role, limit=8):
    out = []
    for c in access.visible_claims(db, project.id, role):
        if c.details.get("draft") or c.status in ("missing", "superseded"):
            continue
        d = c.details
        comp = d.get("component")
        if c.category == "owner" and comp:
            out.append({"topic": f"ownership of {comp}", "question": f"Who owns {comp}?", "expect": [str(d.get("owner", "")).lower()], "claim_id": c.id})
        elif c.category == "procedure" and comp:
            out.append({"topic": f"procedure: {d.get('topic', 'procedure')} for {comp}", "question": f"What is the procedure for {d.get('topic', 'this')} on {comp}?",
                        "expect": [], "claim_id": c.id})
        elif c.category == "decision":
            out.append({"topic": f"decision: {c.statement[:60]}", "question": f"Why did we decide: {c.statement[:120]}", "expect": [], "claim_id": c.id})
        elif c.category == "config_value" and c.status == "conflicting":
            out.append({"topic": f"conflict: {c.subject_key}", "question": f"Which value is correct for {c.subject_key}?", "expect": [], "claim_id": c.id})
    seen, uniq = set(), []
    for s in out:
        if s["question"] not in seen:
            seen.add(s["question"])
            uniq.append(s)
    return uniq[:limit]


def evaluate(db, project, user, role):
    results = []
    eligible = scenarios(db, project, role, limit=100000)
    for sc in eligible[:8]:
        r = rag.ask(db, project, user, role, sc["question"], log_gap=False)
        ok = r["answered"] and bool(r["citations"]) and all(c.get("status") not in ("conflicting", "outdated", "superseded") for c in r["citations"])
        if sc["topic"].startswith("conflict:"):
            ok = False
        if ok and sc["expect"] and sc["expect"][0]:
            ok = sc["expect"][0] in r["answer"].lower()
        results.append({"topic": sc["topic"], "question": sc["question"], "covered": ok, "citations": len(r["citations"])})
    total = len(results)
    score = round(sum(1 for r in results if r["covered"]) / total, 2) if total else 0.0
    level = "ready" if total and score >= 0.8 else "partly_ready" if total and score >= 0.5 else "not_ready"
    return {"assessment_type": "workspace_knowledge_coverage", "not_employee_competency": True, "eligible_scenarios": len(eligible), "omitted_scenarios": max(0, len(eligible)-total), "scenarios": total, "score": score, "readiness": level, "results": results,
            "missed_topics": [r["topic"] for r in results if not r["covered"]]}
