"""Append-only continuity ledger with a hash chain (tamper-evident). No update/delete helpers exist by design."""
import hashlib
import json

from .. import models as m


def _digest(prev, ev):
    body = json.dumps({
        "prev": prev, "project": ev.project_id, "seq": ev.seq, "type": ev.event_type, "entity": [ev.entity_type, ev.entity_id],
        "actor": ev.actor, "record": ev.record_id, "prev_state": ev.previous_state, "new_state": ev.new_state,
        "verification": ev.verification, "permission": ev.permission,
    }, sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def append(db, project_id, event_type, entity_type, entity_id, actor=None, record_id=None, source_id=None,
           previous_state=None, new_state=None, verification="inferred", related=None, permission="project", occurred_at=None):
    last = db.query(m.KnowledgeEvent).filter_by(project_id=project_id).order_by(m.KnowledgeEvent.seq.desc()).first()
    ev = m.KnowledgeEvent(project_id=project_id, seq=(last.seq + 1) if last else 1, event_type=event_type,
                          entity_type=entity_type, entity_id=entity_id, actor=actor, record_id=record_id, source_id=source_id,
                          previous_state=previous_state, new_state=new_state, verification=verification,
                          related_entities=related or [], permission=permission)
    if occurred_at:
        ev.occurred_at = occurred_at
    ev.prev_hash = last.hash if last else ""
    ev.hash = _digest(ev.prev_hash, ev)
    db.add(ev)
    db.flush()
    return ev


def verify_chain(db, project_id):
    prev = ""
    for ev in db.query(m.KnowledgeEvent).filter_by(project_id=project_id).order_by(m.KnowledgeEvent.seq):
        if ev.prev_hash != prev or ev.hash != _digest(prev, ev):
            return {"valid": False, "broken_at_seq": ev.seq}
        prev = ev.hash
    return {"valid": True, "broken_at_seq": None}
