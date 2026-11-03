"""Rule-based knowledge extraction. Deterministic, no model needed. Every item keeps record id + excerpt."""
import re
from dataclasses import dataclass, field

SUFFIXES = ("service", "api", "db", "pipeline", "dashboard", "worker", "gateway")
COMP_RE = re.compile(r"\b([a-z][a-z0-9]+(?:-[a-z0-9]+)*-(?:%s))\b" % "|".join(SUFFIXES), re.I)
NUMWORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def slug(s: str, n=60) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n]


def comp_base(key: str) -> str:
    k = key.lower().strip("/ ")
    for suf in SUFFIXES:
        if k.endswith("-" + suf):
            return k[: -(len(suf) + 1)]
    return k


def person_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").lower().lstrip("@"))


@dataclass
class Item:
    category: str
    subject_key: str
    statement: str
    details: dict = field(default_factory=dict)
    status: str = "evidence_backed"
    excerpt: str = ""


def sentences(text: str):
    for line in re.split(r"\n+", text):
        line = line.strip()
        if not line:
            continue
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z@#\-\[])", line):
            s = s.strip()
            if len(s) > 3:
                yield s


CONCEPTS = [
    ("retry_attempts", re.compile(r"(?i)\b(?:retr(?:y|ies)|attempts?|max_attempts|max_retries)\b")),
    ("token_expiry", re.compile(r"(?i)\b(?:expir\w*|ttl|expiry)\b")),
    ("timeout", re.compile(r"(?i)\btimeouts?\b")),
]
CONST_RE = re.compile(r"\b([A-Z][A-Z0-9_]{3,})\s*=\s*(\d+)\b")
PROSE_NUM = re.compile(r"(?i)\b(\d+|%s)\s*(?:times|retries|attempts|tries|minutes|min|seconds|secs|hours)\b" % "|".join(NUMWORDS))
PROSE_AFTER = re.compile(r"(?i)\b(?:retr(?:y|ies)|attempts?)\s*(?:=|:|is|are|of|to|at)\s*(\d+|%s)\b" % "|".join(NUMWORDS))


def _num(tok):
    tok = tok.lower()
    return NUMWORDS.get(tok) or int(tok)


def _concept(text):
    for name, pat in CONCEPTS:
        if pat.search(text):
            return name
    return None


def _title_component(title: str, content: str):
    m = COMP_RE.search(title) or None
    if m:
        return m.group(1).lower()
    pm = re.search(r"([A-Za-z][\w\-]+)/[\w./\-]+\.(?:py|js|ts|go|java|rb|rs)", title + "\n" + content[:300])
    if pm:
        return pm.group(1).lower()
    return None


def extract(record_type: str, title: str, content: str, author: str = None, meta: dict = None):
    """Return list[Item]. Source-level facts (record id, author, date) are attached by the caller."""
    meta = meta or {}
    items = []
    seen = set()
    ctx_comp = _title_component(title, content)

    def add(it):
        key = (it.category, it.subject_key, it.statement.lower())
        if key not in seen:
            seen.add(key)
            items.append(it)

    if record_type == "codeowners":
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] not in ("*",):
                comp = comp_base(parts[0].strip("/").split("/")[0]) or parts[0]
                owners = [p.lstrip("@") for p in parts[1:] if p.startswith("@")]
                for o in owners:
                    add(Item("owner", f"owner:{comp}:{person_key(o)}", f"{o} is the code owner of {comp}",
                             {"owner": o, "component": comp, "component_kind": "module", "source": "CODEOWNERS"}, "evidence_backed", line))
        return items

    for s in sentences(content):
        low = s.lower()
        comps = [c.lower() for c in COMP_RE.findall(s)]
        comp = comps[0] if comps else ctx_comp

        for mm in re.finditer(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[\w\-/{}:.]*)", s):
            ep = f"{mm.group(1)} {mm.group(2)}"
            add(Item("api", f"api:{ep}", f"Endpoint {ep}", {"endpoint": ep, "component": comp}, "evidence_backed", s))

        for c in comps:
            add(Item("component", f"component:{c}", f"{c} is a component of the project", {"component": c}, "evidence_backed", s))

        # ownership
        om = re.search(r"(@[\w.\-]{2,30}|\b[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+){0,2}|\b[a-z][\w.\-]{1,30})\s+(?i:owns|maintains|is the owner of|is responsible for|is sole owner of)\s+([A-Za-z][\w\-]+)", s)
        om2 = re.search(r"(?i)\b(?:owner|owned by|maintained by|maintainer|sole owner)\s*(?:is|:|-)?\s*@?([A-Za-z][\w.\-]{1,30})", s)
        owner = comp_target = None
        if om and om.group(1).lower() not in ("who", "nobody", "team", "no", "and"):
            owner, comp_target = om.group(1), om.group(2).lower()
        elif om2 and comp:
            owner, comp_target = om2.group(1), comp
        if owner and comp_target:
            base = comp_base(comp_target)
            add(Item("owner", f"owner:{base}:{person_key(owner)}", f"{owner} owns {comp_target}",
                     {"owner": owner, "component": base, "component_name": comp_target}, "evidence_backed", s))

        # decisions
        if re.search(r"(?i)\b(decided|decision|we chose|we agreed|agreed to|we will use|switch(?:ed)? to|adopt(?:ed)?|supersedes|replaces)\b", s):
            alt = re.search(r"(?i)\b(?:instead of|rather than|over)\s+([A-Za-z0-9][\w\-./ ]{1,40}?)(?=[.,;]|\s+because|\s+due|\s+since|\s+for\b|$)", s)
            why = re.search(r"(?i)\b(?:because|due to|reason:?)\s+(.{6,200})", s)
            sup = re.search(r"(?i)\b(?:supersedes|replaces|overrides)\s+(.{3,100}?)(?=[.;]|$)", s)
            stmt = s.rstrip(". ")
            by = author
            dm = re.search(r"(?i)\bdecided by\s+@?([A-Za-z][\w.\-]+)", s)
            if dm:
                by = dm.group(1)
            add(Item("decision", f"decision:{slug(stmt, 70)}", stmt,
                     {"alternatives": [alt.group(1).strip()] if alt else [], "rationale": why.group(1).strip().rstrip(".") if why else "",
                      "supersedes": sup.group(1).strip().strip("\"'") if sup else "", "decided_by": by, "component": comp},
                     "evidence_backed" if why else "inferred", s))

        # tasks
        tm = re.search(r"(?i)(?:\bTODO\b[:\s]*|\btask\s*[:\-]\s*|^[-*]\s*\[( |x)\]\s*)(.+)", s)
        if tm:
            title = tm.group(2).strip() if tm.lastindex and tm.lastindex >= 2 else s
            asg = re.search(r"(?i)(?:assigned to\s+@?|assignee[:\s]+@?|owner[:\s]+@?|@)([A-Za-z][\w.\-]+)", s)
            if not asg:
                asg = re.search(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) (?:will|to)\b", s)
            done = bool(tm.group(1) and tm.group(1).lower() == "x") if tm.lastindex and tm.lastindex >= 2 else False
            add(Item("task", f"task:{slug(title, 70)}", title.rstrip("."), {"assignee": asg.group(1) if asg else None, "done": done, "component": comp},
                     "evidence_backed", s))

        # bugs, blockers, risks
        if record_type == "issue" and not re.search(r"(?i)^(?:feature|enhancement)", title):
            pass
        bug_words = r"(?i)\b(bug|crash|regression|fails?|failure|broken" + (r"|incident|outage" if record_type == "issue" else "") + r")\b"
        if re.search(bug_words, s) and record_type in ("issue", "pull_request", "document", "commit", "message"):
            resolved = bool(re.search(r"(?i)\b(fix(?:ed|es)?|resolved|closes?|closed|patched)\b", s)) or meta.get("state") == "closed"
            add(Item("bug", f"bug:{slug(s, 70)}", s.rstrip("."), {"resolved": resolved, "component": comp, "assignees": meta.get("assignees", [])},
                     "evidence_backed", s))
        if re.search(r"(?i)\b(blocked by|blocker|blocked on)\b", s):
            add(Item("blocker", f"blocker:{slug(s, 70)}", s.rstrip("."), {"component": comp}, "evidence_backed", s))
        if re.search(r"(?i)\brisk\s*:|\bat risk\b|\bsingle point of failure\b", s):
            add(Item("risk", f"risk:{slug(s, 70)}", s.rstrip("."), {"component": comp}, "evidence_backed", s))

        # dependencies
        dm = re.search(r"(?i)\b([a-z][\w\-]+)\s+(?:depends on|relies on|calls|uses)\s+([a-z][\w\-]+)", s)
        if dm and (COMP_RE.fullmatch(dm.group(1)) or COMP_RE.fullmatch(dm.group(2))):
            a, b = dm.group(1).lower(), dm.group(2).lower()
            add(Item("dependency", f"dependency:{a}>{b}", f"{a} depends on {b}", {"from": a, "to": b}, "evidence_backed", s))

        # procedures
        topic = None
        for t, pat in (("rollback", r"roll ?back"), ("deploy", r"deploy"), ("rotation", r"rotat"), ("escalation", r"escalat|on-call"), ("runbook", r"runbook")):
            if re.search(pat, low):
                topic = t
                break
        if topic and comp and not s.endswith("?"):
            add(Item("procedure", f"procedure:{comp_base(comp)}:{topic}", s.rstrip("."), {"component": comp_base(comp), "topic": topic},
                     "evidence_backed", s))
        elif topic and re.search(r"(?i)\b(every (?:mon|tues|wednes|thurs|fri|satur|sun)day|manually|ritual)\b", s):
            add(Item("procedure", f"procedure:{comp_base(comp or 'general')}:{topic}", s.rstrip("."), {"component": comp_base(comp or "general"), "topic": topic},
                     "inferred", s))

        # config values (conflict detection)
        cm = CONST_RE.search(s)
        concept = _concept(cm.group(1)) if cm else None
        val = int(cm.group(2)) if cm and concept else None
        if val is None:
            concept = _concept(s)
            nm = PROSE_AFTER.search(s) or (PROSE_NUM.search(s) if concept else None)
            if concept and nm:
                val = _num(nm.group(1))
        if concept and val is not None:
            base = comp_base(comp) if comp else "general"
            add(Item("config_value", f"value:{base}:{concept}", f"{base}: {concept.replace('_', ' ')} = {val}",
                     {"concept": concept, "value": val, "component": base}, "evidence_backed", s))

        # questions
        if s.endswith("?") and len(s) > 20 and record_type in ("document", "message", "issue"):
            add(Item("question", f"question:{slug(s, 70)}", s, {}, "inferred", s))

    if record_type == "commit" and author:
        for c in COMP_RE.findall(title + " " + content):
            add(Item("contribution", f"contribution:{c.lower()}:{person_key(author)}", f"{author} contributed to {c.lower()}",
                     {"person": author, "component": c.lower()}, "inferred", title))
    if record_type == "pull_request" and author and meta.get("merged") and ctx_comp:
        add(Item("contribution", f"contribution:{ctx_comp}:{person_key(author)}", f"{author} contributed to {ctx_comp}",
                 {"person": author, "component": ctx_comp}, "inferred", title))
    return items
