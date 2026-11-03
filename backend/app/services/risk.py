"""Bus factor and Departure Impact Simulator. Every number is computed from graph rows; there are no static scores."""
import networkx as nx

from .. import models as m
from . import graph as G

QUALIFIED = ("owns", "verified_holds", "backup_owner")
QUALIFIED_VERIFICATION = ("verified", "evidence_backed")
HOLDER_DEFINITION = ("A qualified holder is a person linked to a component by a documented owner statement or CODEOWNERS entry, "
                     "a verified knowledge claim, or a backup-owner record, where that link is Verified or Evidence-backed. "
                     "Commit or PR contributions alone and Inferred links do not count.")
LEVEL_RULES = ("critical: a component would have no remaining qualified holder AND other components depend on it; "
               "high: a component would have no remaining qualified holder; "
               "medium: open tasks/bugs, decisions without reasoning, or components left with a single holder; low: none of these.")


def level_for_count(n):
    return {0: "unowned", 1: "critical", 2: "high", 3: "medium"}.get(n, "lower")


def _components(db, pid):
    return db.query(m.GraphNode).filter(m.GraphNode.project_id == pid, m.GraphNode.node_type.in_(("service", "module"))).all()


def holders_map(db, pid, exclude_person_id=None):
    nodes = {n.id: n for n in db.query(m.GraphNode).filter_by(project_id=pid).all()}
    out = {c.id: {} for c in _components(db, pid)}
    for e in db.query(m.GraphEdge).filter(m.GraphEdge.project_id == pid, m.GraphEdge.relation.in_(QUALIFIED)).all():
        if e.verification not in QUALIFIED_VERIFICATION or e.dst_id not in out or e.src_id == exclude_person_id:
            continue
        p = nodes.get(e.src_id)
        if p and p.node_type == "person":
            out[e.dst_id].setdefault(p.id, []).append(e.relation)
    return out, nodes


def bus_factor(db, pid):
    hm, nodes = holders_map(db, pid)
    rows = []
    for cid, hs in hm.items():
        c = nodes[cid]
        rows.append({"component": c.name, "key": c.key, "bus_factor": len(hs), "level": level_for_count(len(hs)),
                     "holders": [{"person": nodes[p].name, "key": nodes[p].key, "roles": sorted(set(r))} for p, r in hs.items()],
                     "role_counts": {"documented_owner": sum("owns" in r for r in hs.values()),
                                     "verified_holder": sum("verified_holds" in r for r in hs.values()),
                                     "backup_owner": sum("backup_owner" in r for r in hs.values())}})
    rows.sort(key=lambda r: (r["bus_factor"], r["key"]))
    return {"definition": HOLDER_DEFINITION, "components": rows}


def simulate(db, pid, person_key_, user=None, persist=True):
    p = G.resolve_person(db, pid, person_key_)
    if not p:
        return None
    g = G.nx_graph(db, pid)
    dep = nx.DiGraph()
    for u, v, d in g.edges(data=True):
        if d["relation"] == "depends_on":
            dep.add_edge(u, v)
    hm_all, nodes = holders_map(db, pid)
    hm_after, _ = holders_map(db, pid, exclude_person_id=p.id)
    mine = [cid for cid, hs in hm_all.items() if p.id in hs]
    comp_rows, orphaned, single = [], [], []
    for cid in mine:
        after = hm_after[cid]
        dependents = sorted(nodes[x].name for x in (nx.ancestors(dep, cid) if cid in dep else []))
        row = {"component": nodes[cid].name, "key": nodes[cid].key, "roles": sorted(set(hm_all[cid][p.id])),
               "remaining_holders": [nodes[x].name for x in after], "dependents": dependents}
        comp_rows.append(row)
        if not after:
            orphaned.append(row)
        elif len(after) == 1:
            single.append(row)
    edges = db.query(m.GraphEdge).filter_by(project_id=pid).all()
    task_edges = [e for e in edges if e.src_id == p.id and e.relation == "assigned_to" and not nodes[e.dst_id].props.get("done")]
    bug_edges = [e for e in edges if e.src_id == p.id and e.relation == "working_on" and not nodes[e.dst_id].props.get("resolved")]
    dec_edges = [e for e in edges if e.src_id == p.id and e.relation == "decided"]
    tasks, bugs, decided = [nodes[e.dst_id] for e in task_edges], [nodes[e.dst_id] for e in bug_edges], [nodes[e.dst_id] for e in dec_edges]
    ids = lambda es: sorted({e.claim_id for e in es if e.claim_id})
    all_dec = db.query(m.GraphNode).filter_by(project_id=pid, node_type="decision").count()
    verified_rat = {c.subject_key.replace("rationale:", "", 1) for c in db.query(m.Claim).filter_by(project_id=pid, category="rationale", status="verified")}
    undoc = [d for d in decided if not d.props.get("rationale") and d.key not in verified_rat]
    # knowledge only this person's records support
    sole, sole_ids = 0, []
    for c in db.query(m.Claim).filter(m.Claim.project_id == pid, m.Claim.status.in_(G.LIVE)).all():
        evs = db.query(m.EvidenceLink).filter_by(claim_id=c.id).all()
        authors = set()
        for ev in evs:
            r = db.get(m.SourceRecord, ev.record_id) if ev.record_id else None
            authors.add(G.norm_person(r.author) if r and r.author else None)
        if authors and authors == {p.key} :
            sole += 1
            sole_ids.append(c.id)
    gaps = db.query(m.KnowledgeGap).filter_by(project_id=pid, status="open").all()
    comp_keys = {r["key"] for r in comp_rows}
    related_gaps = [g_ for g_ in gaps if (g_.entity_key or "").split(":")[0] in comp_keys or g_.entity_key in {d.key for d in decided}]

    if orphaned and any(r["dependents"] for r in orphaned):
        level = "critical"
    elif orphaned:
        level = "high"
    elif tasks or bugs or undoc or single:
        level = "medium"
    else:
        level = "low"

    key_to_id = {n.key: n.id for n in nodes.values() if n.node_type in ("service", "module")}

    def _claims_for(comp_key, person_id):
        """Claim ids of the qualified-holder links behind a statement, so every reason can be traced to evidence."""
        rows = db.query(m.GraphEdge).filter(m.GraphEdge.project_id == pid, m.GraphEdge.dst_id == key_to_id.get(comp_key),
                                            m.GraphEdge.relation.in_(QUALIFIED)).all()
        return sorted({e.claim_id for e in rows if e.claim_id and (person_id is None or e.src_id == person_id)})

    why = []
    for r in orphaned:
        txt = f"{p.name} is the only qualified holder of {r['component']}; nobody else would be left."
        if r["dependents"]:
            txt += f" Depended on by: {', '.join(r['dependents'])}."
        why.append({"text": txt, "kind": "orphaned_component", "component": r["key"], "claim_ids": _claims_for(r["key"], p.id)})
    for r in single:
        why.append({"text": f"After {p.name} leaves, {r['component']} would rest on one person ({r['remaining_holders'][0]}).", "kind": "single_holder", "component": r["key"], "claim_ids": _claims_for(r["key"], None)})
    if decided:
        why.append({"text": f"Decision maker on {len(decided)} of {all_dec} decisions; {len(undoc)} have no recorded reasoning.", "kind": "decisions",
                    "decisions": len(decided), "total_decisions": all_dec, "without_reasoning": len(undoc), "claim_ids": ids(dec_edges)})
    if tasks:
        why.append({"text": f"{len(tasks)} open task(s) assigned: {', '.join(t.name for t in tasks[:5])}.", "kind": "tasks", "claim_ids": ids(task_edges)})
    if bugs:
        why.append({"text": f"{len(bugs)} unresolved bug(s) in progress: {', '.join(b.name for b in bugs[:5])}.", "kind": "bugs", "claim_ids": ids(bug_edges)})
    if sole:
        why.append({"text": f"{sole} claim(s) are supported only by records written by {p.name}.", "kind": "single_source_knowledge", "claim_ids": sole_ids[:50]})
    result = {
        "person": {"key": p.key, "name": p.name, "user_id": p.user_id},
        "level": level, "level_rules": LEVEL_RULES, "holder_definition": HOLDER_DEFINITION,
        "components": comp_rows, "orphaned_components": [r["key"] for r in orphaned],
        "open_tasks": [t.name for t in tasks], "unresolved_bugs": [b.name for b in bugs],
        "decisions": {"decided": len(decided), "total": all_dec, "without_reasoning": len(undoc),
                      "share": round(len(decided) / all_dec, 2) if all_dec else 0.0},
        "single_source_claims": sole,
        "related_gaps": [{"id": x.id, "type": x.gap_type, "description": x.description} for x in related_gaps],
        "why": why,
        "recommendation": (f"Start an AI Handover Interview with {p.name} and assign a backup owner for: "
                           + ", ".join(r["component"] for r in orphaned)) if orphaned else
                          (f"Review open items with {p.name} before departure." if level != "low" else "No continuity action needed."),
    }
    if persist:
        db.add(m.RiskRecord(project_id=pid, simulation_person_key=p.key, title=f"Departure of {p.name}", level=level, explanation=result))
        from . import ledger
        ledger.append(db, pid, "simulation_run", "person", p.key, actor=getattr(user, "id", None), new_state={"level": level}, verification="inferred")
    return result


def people_overview(db, pid):
    out = []
    for p in db.query(m.GraphNode).filter_by(project_id=pid, node_type="person").all():
        r = simulate(db, pid, p.key, persist=False)
        out.append({"key": p.key, "name": p.name, "user_id": p.user_id, "level": r["level"], "components": len(r["components"])})
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    out.sort(key=lambda x: (order[x["level"]], x["name"]))
    return out
