"""Knowledge graph persisted in DB tables (graph_nodes / dependencies). NetworkX is used only to traverse a copy."""
import networkx as nx

from .. import models as m
from .extract import comp_base, person_key

LIVE = ("verified", "evidence_backed", "inferred", "conflicting", "outdated")


def norm_person(name: str) -> str:
    n = (name or "").strip().lstrip("@")
    if "@" in n:
        n = n.split("@", 1)[0]
    return person_key(n)


def ensure_node(db, pid, ntype, key, name=None, props=None):
    n = db.query(m.GraphNode).filter_by(project_id=pid, node_type=ntype, key=key).first()
    if not n:
        n = m.GraphNode(project_id=pid, node_type=ntype, key=key, name=name or key, props=props or {})
        db.add(n)
        db.flush()
    elif props:
        n.props = {**n.props, **props}
    return n


def resolve_person(db, pid, name):
    k = norm_person(name)
    if not k:
        return None
    for n in db.query(m.GraphNode).filter_by(project_id=pid, node_type="person").all():
        if n.key == k or k in (n.props or {}).get("aliases", []):
            return n
    return None


def ensure_person(db, pid, name):
    n = resolve_person(db, pid, name)
    if n:
        al = set(n.props.get("aliases", []))
        al.add(norm_person(name))
        al.discard(n.key)
        n.props = {**n.props, "aliases": sorted(al), "display_aliases": sorted(set(n.props.get("display_aliases", []) + [name]))}
        return n
    n = ensure_node(db, pid, "person", norm_person(name), (name or "").strip().lstrip("@"), {"aliases": [], "display_aliases": [name]})
    # link to an organisation member when name/email matches
    org_id = db.get(m.Project, pid).org_id
    for u in (db.query(m.User).join(m.Membership, m.Membership.user_id == m.User.id).filter(m.Membership.org_id == org_id).all()):
        if person_key(u.name) == n.key or person_key(u.email.split("@")[0]) == n.key or person_key(u.name.split()[0]) == n.key:
            n.user_id, n.name = u.id, u.name
            break
    return n


def merge_people(db, pid, keep_key, merge_key):
    keep = db.query(m.GraphNode).filter_by(project_id=pid, node_type="person", key=keep_key).first()
    other = db.query(m.GraphNode).filter_by(project_id=pid, node_type="person", key=merge_key).first()
    if not keep or not other or keep.id == other.id:
        return None
    keep.props = {**keep.props, "aliases": sorted(set(keep.props.get("aliases", [])) | set(other.props.get("aliases", [])) | {other.key}),
                  "display_aliases": sorted(set(keep.props.get("display_aliases", [])) | set(other.props.get("display_aliases", [])) | {other.name})}
    if not keep.user_id and other.user_id:
        keep.user_id = other.user_id
    for e in db.query(m.GraphEdge).filter((m.GraphEdge.src_id == other.id) | (m.GraphEdge.dst_id == other.id)).all():
        db.delete(e)
    db.delete(other)
    db.flush()
    return keep


def _vmap(status):
    return status if status in ("verified", "evidence_backed") else "inferred"


def rebuild_graph(db, pid):
    db.query(m.GraphEdge).filter_by(project_id=pid).delete()
    db.flush()
    for c in db.query(m.Component).filter_by(project_id=pid).all():
        ensure_node(db, pid, "service" if c.kind != "module" else "module", c.key, c.name, {"kind": c.kind})
    edges = set()

    def edge(src, dst, rel, ver, claim=None, rec=None):
        k = (src.id, dst.id, rel)
        if k in edges or src.id == dst.id:
            return
        edges.add(k)
        db.add(m.GraphEdge(project_id=pid, src_id=src.id, dst_id=dst.id, relation=rel, verification=ver,
                           claim_id=claim.id if claim else None, record_id=rec))

    def comp_node(name):
        c = db.query(m.Component).filter_by(project_id=pid, key=comp_base(name)).first()
        if not c:
            return None
        return ensure_node(db, pid, "service" if c.kind != "module" else "module", c.key, c.name)

    for sk in db.query(m.PeopleKnowledge).filter_by(project_id=pid, approved=True).all():
        person = db.query(m.GraphNode).filter_by(project_id=pid, node_type="person", user_id=sk.user_id).first()
        if not person:
            u = db.get(m.User, sk.user_id)
            person = ensure_person(db, pid, u.name) if u else None
        if person:
            sn = ensure_node(db, pid, "skill", norm_person(sk.skill) or sk.skill.lower(), sk.skill, {"level": sk.level})
            edge(person, sn, "has_skill", "verified")
            for sysname in (sk.profile or {}).get("prior_systems") or []:
                cn = comp_node(sysname)
                if cn:
                    edge(person, cn, "has_experience_with", "inferred")
    claims = db.query(m.Claim).filter(m.Claim.project_id == pid, m.Claim.status.in_(LIVE)).all()
    for c in claims:
        d, ver = c.details, _vmap(c.status)
        if c.details.get("draft"):
            continue
        if c.category == "owner":
            p, cn = ensure_person(db, pid, d["owner"]), comp_node(d["component"])
            if cn:
                edge(p, cn, "owns", ver, c)
        elif c.category in ("holder", "backup"):
            p, cn = ensure_person(db, pid, d["person"]), comp_node(d["component"])
            if cn:
                edge(p, cn, "verified_holds" if c.category == "holder" else "backup_owner", ver, c)
        elif c.category == "contribution":
            p, cn = ensure_person(db, pid, d["person"]), comp_node(d["component"])
            if cn:
                edge(p, cn, "contributes", "inferred", c)
        elif c.category == "dependency":
            a, b = comp_node(d["from"]), comp_node(d["to"])
            if a and b:
                edge(a, b, "depends_on", ver, c)
        elif c.category == "decision":
            dn = ensure_node(db, pid, "decision", c.subject_key, c.statement[:80], {"rationale": bool(d.get("rationale")), "claim_id": c.id})
            if d.get("decided_by"):
                edge(ensure_person(db, pid, d["decided_by"]), dn, "decided", ver, c)
            if d.get("component") and comp_node(d["component"]):
                edge(dn, comp_node(d["component"]), "concerns", ver, c)
            ev = db.query(m.EvidenceLink).filter_by(claim_id=c.id).first()
            if ev and ev.record_id:
                rec = db.get(m.SourceRecord, ev.record_id)
                if rec and rec.record_type == "document":
                    doc = ensure_node(db, pid, "document", rec.id, rec.title)
                    edge(dn, doc, "documented_in", ver, c)
        elif c.category == "task":
            tn = ensure_node(db, pid, "task", c.subject_key, c.statement[:80], {"done": d.get("done", False)})
            if d.get("assignee"):
                edge(ensure_person(db, pid, d["assignee"]), tn, "assigned_to", ver, c)
        elif c.category == "bug":
            bn = ensure_node(db, pid, "bug", c.subject_key, c.statement[:80], {"resolved": d.get("resolved", False)})
            if d.get("component") and comp_node(d["component"]):
                edge(bn, comp_node(d["component"]), "affects", ver, c)
            for a in d.get("assignees") or []:
                edge(ensure_person(db, pid, a), bn, "working_on", ver, c)
        elif c.category == "api":
            an = ensure_node(db, pid, "api", c.subject_key, d["endpoint"])
            if d.get("component") and comp_node(d["component"]):
                edge(an, comp_node(d["component"]), "part_of", ver, c)
    # supersession between decisions
    for c in db.query(m.Claim).filter(m.Claim.project_id == pid, m.Claim.category == "decision", m.Claim.superseded_by.isnot(None)).all():
        newer = db.get(m.Claim, c.superseded_by)
        if newer:
            edge(ensure_node(db, pid, "decision", newer.subject_key, newer.statement[:80]),
                 ensure_node(db, pid, "decision", c.subject_key, c.statement[:80]), "supersedes", "evidence_backed", c)
    db.flush()


def nx_graph(db, pid):
    g = nx.MultiDiGraph()
    for n in db.query(m.GraphNode).filter_by(project_id=pid).all():
        g.add_node(n.id, type=n.node_type, key=n.key, name=n.name, user_id=n.user_id)
    for e in db.query(m.GraphEdge).filter_by(project_id=pid).all():
        g.add_edge(e.src_id, e.dst_id, key=e.relation, relation=e.relation, verification=e.verification, claim_id=e.claim_id)
    return g
