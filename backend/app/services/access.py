"""Permission filter. Applied BEFORE retrieval/answer building. Claim visibility = strictest of its evidence."""
from .. import models as m

RANK = {"project": 0, "restricted": 1}
SEE = {"incoming": 0, "contributor": 0, "manager": 1, "admin": 1}


def can_see_level(role, level):
    return SEE.get(role, -1) >= RANK.get(level, 1)


def claim_level(db, claim):
    lvl = 0
    for ev in db.query(m.EvidenceLink).filter_by(claim_id=claim.id).all():
        if ev.record_id:
            r = db.get(m.SourceRecord, ev.record_id)
            if r:
                lvl = max(lvl, RANK.get(r.visibility, 1))
    return "restricted" if lvl else "project"


def visible_claims(db, pid, role, statuses=None):
    out = []
    for c in db.query(m.Claim).filter_by(project_id=pid).all():
        if c.status != "missing" and can_see_level(role, claim_level(db, c)):
            out.append(c)
    comps, subjects = set(), set()
    for c in out:
        subjects.add(c.subject_key)
        for k in ("component", "from", "to"):
            if isinstance(c.details.get(k), str):
                comps.add(c.details[k])
    for c in db.query(m.Claim).filter_by(project_id=pid, status="missing").all():
        d = c.details
        if d.get("component") and d["component"] not in comps:
            continue  # a missing-claim must not reveal a component only restricted sources mention
        if d.get("decision") and d["decision"] not in subjects:
            continue
        out.append(c)
    return [c for c in out if not statuses or c.status in statuses]


def visible_record(rec, role):
    return can_see_level(role, rec.visibility)
