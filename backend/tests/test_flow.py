from conftest import H, add_member, register
from data import ARCH, INJECT, RESTRICTED, RUNBOOK, SECRET


def up(client, tok, pid, name, text, visibility="project", author=""):
    return client.post(f"/api/projects/{pid}/uploads", headers=H(tok), files={"file": (name, text.encode(), "text/plain")},
                       data={"visibility": visibility, "author": author})


def setup_team(client):
    admin = register(client, "alok@acme.io", "Alok Kumar")
    org, pid = admin["org_id"], admin["project_id"]
    priya = add_member(client, admin, org, "priya@acme.io", "Priya Sharma", "contributor")
    gargi = add_member(client, admin, org, "gargi@acme.io", "Gargi Yadav", "manager")
    yen = add_member(client, admin, org, "yenika@acme.io", "Yenika Choudhary", "incoming")
    for u in (priya, yen):
        assert client.post(f"/api/projects/{pid}/members", json={"user_id": u["user_id"]}, headers=H(admin["token"])).status_code == 201
    return admin, priya, gargi, yen, org, pid


def load_docs(client, admin, pid):
    for n, t in [("architecture.md", ARCH), ("runbook.md", RUNBOOK)]:
        r = up(client, admin["token"], pid, n, t, author="Priya Sharma")
        assert r.status_code == 201, r.text
        assert r.json()["stored"] == 1


def test_register_login_and_rbac(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    assert client.get("/api/auth/me", headers=H(priya["token"])).json()["orgs"][0]["role"] == "contributor"
    # contributor cannot add members / see audit / sync / simulate
    assert client.post(f"/api/orgs/{org}/members", json={"email": "x@acme.io", "role": "admin"}, headers=H(priya["token"])).status_code == 403
    assert client.get(f"/api/orgs/{org}/audit", headers=H(priya["token"])).status_code == 403
    assert client.post(f"/api/projects/{pid}/simulations", json={"person": "priya"}, headers=H(priya["token"])).status_code == 403
    assert client.get("/api/projects", headers=H(yen["token"])).json()[0]["id"] == pid
    assert client.get(f"/api/projects/{pid}/overview").status_code == 401


def test_login_rate_limit_and_bad_password(client):
    register(client, "a@x.io", "A")
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "a@x.io", "password": "wrong-password-1"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "a@x.io", "password": "correct-horse-1"}).status_code == 429


def test_weak_password_rejected(client):
    r = client.post("/api/auth/register", json={"email": "a@x.io", "name": "A", "password": "short", "org_name": "O"})
    assert r.status_code == 422


def test_session_revoke(client):
    a = register(client, "a@x.io", "A")
    assert client.get("/api/auth/me", headers=H(a["token"])).status_code == 200
    import time
    time.sleep(1.1)
    client.post("/api/auth/revoke-all-sessions", headers=H(a["token"]))
    assert client.get("/api/auth/me", headers=H(a["token"])).status_code == 401


def test_cross_org_idor(client):
    a = register(client, "a@x.io", "A", org="OrgA")
    b = register(client, "b@y.io", "B", org="OrgB")
    up(client, a["token"], a["project_id"], "n.md", ARCH)
    rec = client.get(f"/api/projects/{a['project_id']}/records", headers=H(a["token"])).json()[0]["id"]
    for path in (f"/api/projects/{a['project_id']}/overview", f"/api/projects/{a['project_id']}/records/{rec}", f"/api/projects/{a['project_id']}/claims"):
        assert client.get(path, headers=H(b["token"])).status_code == 404
    # b's own project cannot read a's record id
    assert client.get(f"/api/projects/{b['project_id']}/records/{rec}", headers=H(b["token"])).status_code == 404
    assert client.delete(f"/api/projects/{b['project_id']}/records/{rec}", headers=H(b["token"])).status_code == 404


def test_upload_validation(client):
    admin = register(client, "a@x.io", "A")
    pid, t = admin["project_id"], admin["token"]
    assert client.post(f"/api/projects/{pid}/uploads", headers=H(t), files={"file": ("evil.exe", b"MZ", "application/octet-stream")}).status_code == 415
    r = client.post(f"/api/projects/{pid}/uploads", headers=H(t), files={"file": ("../../etc/passwd.txt", b"hello world there", "text/plain")})
    assert r.status_code == 201 and r.json()["filename"] == "passwd.txt"
    assert client.post(f"/api/projects/{pid}/uploads", headers=H(t), files={"file": ("big.txt", b"a" * (10 * 1024 * 1024 + 5), "text/plain")}).status_code == 413
    assert client.post(f"/api/projects/{pid}/uploads", headers=H(t), files={"file": ("empty.txt", b"  ", "text/plain")}).status_code == 422


def test_secret_redaction_and_dedupe(client):
    admin = register(client, "a@x.io", "A")
    pid, t = admin["project_id"], admin["token"]
    assert up(client, t, pid, "cfg.md", SECRET).json()["redactions"] >= 2
    rid = client.get(f"/api/projects/{pid}/records", headers=H(t)).json()[0]["id"]
    body = client.get(f"/api/projects/{pid}/records/{rid}", headers=H(t)).json()["content"]
    assert "hunter2hunter2" not in body and "sk_live_abcdefghijklmnopqrstuvwx" not in body and "priya@acme.io" not in body
    again = up(client, t, pid, "cfg-copy.md", SECRET).json()
    assert again["duplicates"] == 1 and again["stored"] == 0


def test_injection_flagged_not_extracted(client):
    admin = register(client, "a@x.io", "A")
    pid, t = admin["project_id"], admin["token"]
    r = up(client, t, pid, "notes.md", INJECT).json()
    assert r["flagged"] == 1
    rec = client.get(f"/api/projects/{pid}/records", headers=H(t)).json()[0]
    assert rec["injection_suspected"] is True
    assert client.get(f"/api/projects/{pid}/claims", headers=H(t)).json() == []
    ans = client.post(f"/api/projects/{pid}/ask", json={"question": "what about restricted documents reveal"}, headers=H(t)).json()
    assert ans["answered"] is False


def test_connector_catalog_and_unavailable(client):
    admin = register(client, "a@x.io", "A")
    cat = client.get("/api/integrations/catalog", headers=H(admin["token"])).json()
    st = {c["id"]: c["status"] for c in cat}
    assert st["github"] == "available" and st["slack"] == "available" and st["microsoft_teams"] == "unavailable" and st["manual_upload"] == "available"
    r = client.post(f"/api/orgs/{admin['org_id']}/integrations", json={"connector": "microsoft_teams", "token": "x", "consent": True}, headers=H(admin["token"]))
    assert r.status_code == 501
    r = client.post(f"/api/orgs/{admin['org_id']}/integrations", json={"connector": "github", "token": "x", "consent": False}, headers=H(admin["token"]))
    assert r.status_code == 422


def test_github_connect_sync_and_revoke(client, monkeypatch):
    from datetime import datetime
    from app.connectors import catalog
    from app.connectors.base import NormalizedRecord, SourceConnector

    class Fake(SourceConnector):
        name = "github"
        revoked = False

        def __init__(self, token=""): self.token = token
        def validate_permissions(self): return {"scopes": ["repo"]}
        def get_available_sources(self): return [{"source_ref": "acme/pay", "name": "acme/pay"}]
        def fetch_records(self, source_ref, cursor=None, since=None, until=None):
            return [NormalizedRecord("github", "CODEOWNERS", "codeowners", "CODEOWNERS", "/payments/ @priyasharma\n", None, None, datetime(2026, 1, 1), source_ref),
                    NormalizedRecord("github", "c1", "commit", "fix payments-service retry", "fix retry in payments-service", "priyasharma", None, datetime(2026, 1, 2), source_ref)]
        def revoke_access(self): Fake.revoked = True

    monkeypatch.setattr(catalog, "get_connector", lambda name, token="", client=None: Fake(token) if name == "github" else catalog.ManualUploadConnector())
    admin = register(client, "a@x.io", "A")
    org, pid, t = admin["org_id"], admin["project_id"], admin["token"]
    integ = client.post(f"/api/orgs/{org}/integrations", json={"connector": "github", "token": "ghp_secret_token_value", "consent": True}, headers=H(t))
    assert integ.status_code == 201
    iid = integ.json()["id"]
    assert "ghp_secret" not in str(client.get(f"/api/orgs/{org}/integrations", headers=H(t)).json())
    sid = client.post(f"/api/projects/{pid}/sources", json={"integration_id": iid, "source_ref": "acme/pay"}, headers=H(t)).json()["id"]
    job = client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()
    assert job["stored"] == 2 and job["status"] == "completed"
    # selection: exclude -> next sync stores nothing new
    client.put(f"/api/projects/{pid}/sources/{sid}/selection", json={"included": False}, headers=H(t))
    assert client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()["stored"] == 0
    assert client.delete(f"/api/orgs/{org}/integrations/{iid}", headers=H(t)).json()["status"] == "revoked"
    assert Fake.revoked
    assert client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).status_code == 409
    kinds = [e["type"] for e in client.get(f"/api/projects/{pid}/ledger", headers=H(t)).json()]
    assert "scope_changed" in kinds


def test_claims_conflict_and_states(client):
    admin, *_ , pid = setup_team(client)
    load_docs(client, admin, pid)
    cl = client.get(f"/api/projects/{pid}/claims", headers=H(admin["token"])).json()
    conf = [c for c in cl if c["category"] == "config_value"]
    assert len(conf) == 2 and all(c["status"] == "conflicting" for c in conf)
    gaps = client.get(f"/api/projects/{pid}/gaps", headers=H(admin["token"])).json()
    assert any(g["type"] == "conflict" for g in gaps)
    one = client.get(f"/api/projects/{pid}/claims/{conf[0]['id']}", headers=H(admin["token"])).json()
    assert one["evidence"] and one["evidence"][0]["quote_verified"] is True and "timeout" in one["evidence"][0]["quote"]


def test_departure_impact_and_bus_factor(client):
    admin, *_ , pid = setup_team(client)
    load_docs(client, admin, pid)
    sim = client.post(f"/api/projects/{pid}/simulations", json={"person": "Priya Sharma"}, headers=H(admin["token"])).json()
    assert "payments" in sim["orphaned_components"]
    assert sim["level"] in ("critical", "high")
    assert "qualified holder" in sim["holder_definition"].lower()
    assert any("payments" in w["text"] for w in sim["why"])
    # anjali owns auth; payments depends on auth -> losing anjali orphans auth with dependents
    sim2 = client.post(f"/api/projects/{pid}/simulations", json={"person": "anjalijha"}, headers=H(admin["token"])).json()
    assert sim2["level"] == "critical" and "auth" in sim2["orphaned_components"]
    assert "payments-service" in str(sim2["components"])
    bf = client.get(f"/api/projects/{pid}/risk/bus-factor", headers=H(admin["token"])).json()
    assert {c["key"]: c["bus_factor"] for c in bf["components"]}["payments"] == 1
    assert client.post(f"/api/projects/{pid}/simulations", json={"person": "nobody"}, headers=H(admin["token"])).status_code == 404
    assert client.get(f"/api/projects/{pid}/simulations", headers=H(admin["token"])).json()


def test_ledger_chain_and_tamper(client):
    from app import db as dbm, models as m
    admin, *_ , pid = setup_team(client)
    load_docs(client, admin, pid)
    assert client.get(f"/api/projects/{pid}/ledger/verify", headers=H(admin["token"])).json()["valid"] is True
    s = dbm.SessionLocal()
    ev = s.query(m.KnowledgeEvent).filter_by(project_id=pid).order_by(m.KnowledgeEvent.seq).all()[3]
    ev.new_state = {"status": "verified", "tampered": True}
    s.commit()
    s.close()
    r = client.get(f"/api/projects/{pid}/ledger/verify", headers=H(admin["token"])).json()
    assert r["valid"] is False and r["broken_at_seq"] == 4


def test_unauthorised_retrieval_restricted(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    load_docs(client, admin, pid)
    # contributor cannot upload restricted; admin can
    assert up(client, priya["token"], pid, "hr.md", RESTRICTED, "restricted").status_code == 403
    assert up(client, admin["token"], pid, "hr.md", RESTRICTED, "restricted").status_code == 201
    q = {"question": "What is the salary-service budget?"}
    mgr = client.post(f"/api/projects/{pid}/ask", json=q, headers=H(admin["token"])).json()
    assert mgr["answered"] is True and "900" in mgr["answer"]
    low = client.post(f"/api/projects/{pid}/ask", json=q, headers=H(yen["token"])).json()
    nothing = client.post(f"/api/projects/{pid}/ask", json={"question": "What is the zebra-service budget for quantum llamas?"}, headers=H(yen["token"])).json()
    assert low["answered"] is False and low["answer"] == nothing["answer"] and low["citations"] == []
    # restricted record, claim, graph and ledger invisible to non-managers
    recs = client.get(f"/api/projects/{pid}/records", headers=H(priya["token"])).json()
    assert all(r["visibility"] == "project" for r in recs)
    claims = client.get(f"/api/projects/{pid}/claims", headers=H(priya["token"])).json()
    assert not any("salary" in c["statement"].lower() for c in claims if c["category"] != "question_missing")
    g = client.get(f"/api/projects/{pid}/graph", headers=H(priya["token"])).json()
    assert not any("salary" in n["name"].lower() for n in g["nodes"])
    hr = [r for r in client.get(f"/api/projects/{pid}/records", headers=H(admin["token"])).json() if r["visibility"] == "restricted"][0]
    assert client.get(f"/api/projects/{pid}/records/{hr['id']}", headers=H(priya["token"])).status_code == 404


def test_citation_correctness(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    load_docs(client, admin, pid)
    r = client.post(f"/api/projects/{pid}/ask", json={"question": "Why did we use PostgreSQL instead of MongoDB?"}, headers=H(yen["token"])).json()
    assert r["answered"] and r["citations"]
    c = r["citations"][0]
    rec = client.get(f"/api/projects/{pid}/records/{c['record_id']}", headers=H(admin["token"])).json()
    assert c["quote"] in rec["content"]  # the cited quote really exists in the cited source
    assert "strong consistency" in r["answer"]


def test_full_interview_to_handover_flow(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    load_docs(client, admin, pid)
    A, P, G, Y = (H(x["token"]) for x in (admin, priya, gargi, yen))
    iv = client.post(f"/api/projects/{pid}/interviews", json={"person": "Priya Sharma"}, headers=G).json()
    assert iv["progress"]["total"] >= 2
    base = f"/api/projects/{pid}/interviews/{iv['id']}"
    by_type = {q["context"]["gap_type"]: q for q in iv["questions"]}
    # non-owner cannot answer
    assert client.post(f"{base}/questions/{by_type['conflict']['id']}/answers", json={"answer": "x"}, headers=G).status_code == 403
    # conflict: vague answer -> follow-up; number-word answer resolves
    q = by_type["conflict"]
    r = client.post(f"{base}/questions/{q['id']}/answers", json={"answer": "not sure honestly"}, headers=P).json()
    assert r["follow_up"] and "30" in r["follow_up"]["question"]
    r2 = client.post(f"{base}/questions/{r['follow_up']['id']}/answers", json={"answer": "sixty is correct"}, headers=P).json()
    assert r2["follow_up"] is None
    ap_id = client.post(f"{base}/responses/{r2['response_id']}/confirm", headers=P).json()["approval_id"]
    # priya is only a contributor -> cannot decide approvals at all
    assert client.post(f"/api/projects/{pid}/approvals/{ap_id}/decide", json={"approve": True}, headers=P).status_code == 403
    d = client.post(f"/api/projects/{pid}/approvals/{ap_id}/decide", json={"approve": True}, headers=G)
    assert d.status_code == 200, d.text
    claims = client.get(f"/api/projects/{pid}/claims?category=config_value", headers=A).json()
    assert {c["status"] for c in claims} == {"verified", "superseded"}
    assert [c for c in claims if c["status"] == "verified"][0]["statement"].endswith("60")
    # rollback procedure: short answer -> follow up
    if "missing_procedure" in by_type:
        q = by_type["missing_procedure"]
        r = client.post(f"{base}/questions/{q['id']}/answers", json={"answer": "redeploy"}, headers=P).json()
        assert r["follow_up"]
    # undocumented decision (redis)
    q = by_type["undocumented_decision"]
    r = client.post(f"{base}/questions/{q['id']}/answers", json={"answer": "Redis was picked because refund lookups need sub millisecond reads."}, headers=P).json()
    assert r["follow_up"] is None
    ap2 = client.post(f"{base}/responses/{r['response_id']}/confirm", headers=P).json()["approval_id"]
    # unconfirmed answers can't be approved; confirmed one by the admin works, admin != answerer
    assert client.post(f"/api/projects/{pid}/approvals/{ap2}/decide", json={"approve": True}, headers=A).status_code == 200
    # holder edges: priya now a verified holder via the approved answers; gaps shrink
    sim = client.post(f"/api/projects/{pid}/simulations", json={"person": "priyasharma"}, headers=A).json()
    assert sim["decisions"]["decided"] >= 0
    gaps = client.get(f"/api/projects/{pid}/gaps", headers=A).json()
    assert not any(g["type"] == "conflict" for g in gaps)
    assert not any(g["type"] == "undocumented_decision" and "Redis" in g["description"] for g in gaps)
    assert client.get(f"/api/projects/{pid}/ledger/verify", headers=A).json()["valid"] is True
    # handover doc
    h = client.post(f"/api/projects/{pid}/handovers", json={"person": "priyasharma", "incoming_user_id": yen["user_id"]}, headers=G).json()
    secs = {s["key"]: s for s in h["sections"]}
    assert len(secs) == 11 and secs["limitations"]["items"] and secs["ownership"]["items"] and all(i["evidence"] for i in secs["ownership"]["items"])
    assert any(i["evidence"] for i in secs["decisions"]["items"])
    # incoming user can't see an unapproved handover
    assert client.get(f"/api/projects/{pid}/handovers/{h['id']}", headers=Y).status_code == 404
    hap = client.post(f"/api/projects/{pid}/handovers/{h['id']}/request-approval", headers=G).json()["approval_id"]
    assert client.post(f"/api/projects/{pid}/approvals/{hap}/decide", json={"approve": True}, headers=G).status_code == 403  # own request
    assert client.post(f"/api/projects/{pid}/approvals/{hap}/decide", json={"approve": True}, headers=A).status_code == 200
    got = client.get(f"/api/projects/{pid}/handovers/{h['id']}", headers=Y)
    assert got.status_code == 200 and got.json()["summary"]["status"] == "approved"
    pdf = client.get(f"/api/projects/{pid}/handovers/{h['id']}/pdf", headers=Y)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # rehearsal
    s = client.post(f"/api/projects/{pid}/rehearsal", headers=Y).json()["id"]
    a = client.post(f"/api/projects/{pid}/rehearsal/{s}/ask", json={"question": "What is the payments-service timeout?"}, headers=Y).json()
    assert a["answered"] and a["turns"] == 1
    ev = client.post(f"/api/projects/{pid}/rehearsal/{s}/evaluate", headers=Y).json()
    assert ev["scenarios"] >= 1 and 0 <= ev["score"] <= 1 and ev["readiness"] in ("ready", "partly_ready", "not_ready") and "missed_topics" in ev
    assert "first_actions" in secs and "contacts" in secs and "deployment" in secs
    assert all("claim_ids" in w for w in sim["why"] if w["kind"] in ("orphaned_component", "single_holder"))
    # overview
    ov = client.get(f"/api/projects/{pid}/overview", headers=A).json()
    assert 0 < ov["health_score"] <= 100 and ov["state_counts"]["verified"] >= 2 and len(ov["ingestion_14d"]) == 14


def test_answer_gap_logged_when_unknown(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    load_docs(client, admin, pid)
    r = client.post(f"/api/projects/{pid}/ask", json={"question": "How do we rotate the kafka credentials?"}, headers=H(yen["token"])).json()
    assert r["answered"] is False
    gaps = client.get(f"/api/projects/{pid}/gaps", headers=H(admin["token"])).json()
    assert any(g["type"] == "unanswered_question" for g in gaps)
    miss = client.get(f"/api/projects/{pid}/claims?status=missing", headers=H(admin["token"])).json()
    assert any(c["category"] == "question_missing" for c in miss)


def test_record_deletion_cascades(client):
    admin, *_ , pid = setup_team(client)
    load_docs(client, admin, pid)
    rid = [r for r in client.get(f"/api/projects/{pid}/records", headers=H(admin["token"])).json() if r["title"] == "runbook.md"][0]["id"]
    assert client.delete(f"/api/projects/{pid}/records/{rid}", headers=H(admin["token"])).status_code == 200
    conf = client.get(f"/api/projects/{pid}/claims?category=config_value", headers=H(admin["token"])).json()
    assert len(conf) == 1 and conf[0]["status"] != "conflicting"


def test_member_correction_and_identity_merge(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    load_docs(client, admin, pid)
    cl = [c for c in client.get(f"/api/projects/{pid}/claims?category=api", headers=H(priya["token"])).json()][0]
    ap = client.post(f"/api/projects/{pid}/claims/{cl['id']}/corrections", json={"corrected_statement": "Endpoint GET /payments/refunds"}, headers=H(priya["token"])).json()["approval_id"]
    assert client.post(f"/api/projects/{pid}/approvals/{ap}/decide", json={"approve": True}, headers=H(gargi["token"])).status_code == 200
    assert client.get(f"/api/projects/{pid}/claims/{cl['id']}", headers=H(admin["token"])).json()["status"] == "verified"
    r = client.post(f"/api/projects/{pid}/graph/people/merge", json={"keep": "priyasharma", "merge": "nobody"}, headers=H(gargi["token"]))
    assert r.status_code == 404


def test_delete_all_records_of_a_source_and_retrieval_audit(client, monkeypatch):
    from datetime import datetime
    from app.connectors import catalog
    from app.connectors.base import NormalizedRecord, SourceConnector

    class Fake(SourceConnector):
        def __init__(self, token=""): pass
        def validate_permissions(self): return {}
        def fetch_records(self, source_ref, cursor=None, since=None, until=None):
            return [NormalizedRecord("github", "c1", "commit", "t", "fix payments-service retry", "priyasharma", None, datetime(2026, 1, 2), source_ref)]

    monkeypatch.setattr(catalog, "get_connector", lambda name, token="", client=None: Fake(token))
    a = register(client, "d@x.io", "D")
    org, pid, t = a["org_id"], a["project_id"], a["token"]
    iid = client.post(f"/api/orgs/{org}/integrations", json={"connector": "github", "token": "tok", "consent": True}, headers=H(t)).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources", json={"integration_id": iid, "source_ref": "a/b"}, headers=H(t)).json()["id"]
    assert client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()["stored"] == 1
    r = client.delete(f"/api/projects/{pid}/sources/{sid}/records", headers=H(t)).json()
    assert r["records_deleted"] == 1
    assert client.get(f"/api/projects/{pid}/records", headers=H(t)).json() == []
    client.post(f"/api/projects/{pid}/ask", json={"question": "who owns billing"}, headers=H(t))
    acts = [e["action"] for e in client.get(f"/api/orgs/{org}/audit", headers=H(t)).json()]
    assert "source_records_deleted" in acts and "ai_retrieval" in acts


def test_individual_consent_encryption_confidential_and_scope(client, monkeypatch):
    from datetime import datetime
    from app.connectors import catalog
    from app.connectors.base import NormalizedRecord, SourceConnector
    from app import db as dbm, models as m

    class Fake(SourceConnector):
        def __init__(self, token=""): pass
        def validate_permissions(self): return {}
        def fetch_records(self, source_ref, cursor=None, since=None, until=None):
            return [NormalizedRecord("github", "c1", "commit", "t1", "fix payments-service retry", "priyasharma", None, datetime(2026, 1, 2), source_ref),
                    NormalizedRecord("github", "c2", "commit", "t2", "tune billing-service cache", "gargi", None, datetime(2026, 1, 3), source_ref),
                    NormalizedRecord("github", "c3", "issue", "t3", "salary review plan is confidential", "gargi", None, datetime(2026, 1, 4), source_ref),
                    NormalizedRecord("github", "c4", "pull_request", "t4", "pr text", "gargi", None, datetime(2026, 1, 5), source_ref)]

    monkeypatch.setattr(catalog, "get_connector", lambda name, token="", client=None: Fake(token))
    a = register(client, "e@x.io", "E")
    org, pid, t = a["org_id"], a["project_id"], a["token"]
    iid = client.post(f"/api/orgs/{org}/integrations", json={"connector": "github", "token": "tok", "consent": True,
                                                            "scopes": {"permissions": ["commits", "issues"]}}, headers=H(t)).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources", json={"integration_id": iid, "source_ref": "a/b"}, headers=H(t)).json()["id"]
    r = client.put(f"/api/projects/{pid}/consents", json={"author": "gargi", "granted": False}, headers=H(t))
    assert r.status_code == 200
    job = client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()
    assert job["stored"] == 1  # gargi opted out; pull_request scope not approved
    client.put(f"/api/projects/{pid}/consents", json={"author": "gargi", "granted": True}, headers=H(t))
    job = client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()
    recs = {x["title"]: x for x in client.get(f"/api/projects/{pid}/records", headers=H(t)).json()}
    assert set(recs) == {"t1", "t2", "t3"}  # pull request never stored (scope not approved)
    assert recs["t3"].get("visibility") == "restricted"  # confidential wording
    # withdrawing consent removes what was already stored
    out = client.put(f"/api/projects/{pid}/consents", json={"author": "gargi", "granted": False}, headers=H(t)).json()
    assert out["records_removed"] == 2
    # stored text is encrypted in the database but readable through the API
    with dbm.engine.connect() as c:
        raw = c.exec_driver_sql("select content from source_records").fetchall()
    assert raw and all(x[0].startswith("enc1:") and "payments-service" not in x[0] for x in raw)
    rid = client.get(f"/api/projects/{pid}/records", headers=H(t)).json()[0]["id"]
    assert "payments-service" in client.get(f"/api/projects/{pid}/records/{rid}", headers=H(t)).json()["content"]


def test_github_incremental_cursor_skips_old_prs():
    import httpx
    from datetime import datetime
    from app.connectors.github import GitHubConnector
    seen = {}

    def h(req):
        p = req.url.path
        seen[p.rsplit("/", 1)[-1]] = dict(req.url.params)
        if p.endswith("/pulls"):
            return httpx.Response(200, json=[{"number": 1, "title": "old", "updated_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z", "user": {"login": "a"}},
                                             {"number": 2, "title": "new", "updated_at": "2026-03-01T00:00:00Z", "created_at": "2026-03-01T00:00:00Z", "user": {"login": "a"}}])
        if p.endswith("/commits") or p.endswith("/issues"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)
    c = GitHubConnector("t", httpx.Client(transport=httpx.MockTransport(h)))
    recs = c.fetch_records("a/b", cursor="2026-02-01T00:00:00")
    assert [r.title for r in recs] == ["PR #2: new"] and seen["commits"]["since"].startswith("2026-02-01")


def test_adaptive_followups_are_contextual():
    from types import SimpleNamespace as S
    from app.services import interview
    class FakeDB:
        def get(self, model, id_): return S(gap_type="no_documented_owner", entity_key="payments-service:owner", id="g1")
        def add(self, x): pass
        def flush(self): pass
    q = S(gap_id="g1", parent_question_id=None, question="Who owns payments-service?", context={}, id="q1", position=1)
    fq = interview._followup(FakeDB(), S(id="i1"), q, "Priya owns it")
    assert fq is not None and "backup" in fq.question.lower()
    assert interview._followup(FakeDB(), S(id="i1"), q, "Priya owns it, Gargi is the backup") is None


def test_opt_in_mode_graph_repo_nodes_and_source_changed(client, monkeypatch):
    from datetime import datetime
    from app.connectors import catalog
    from app.connectors.base import NormalizedRecord, SourceConnector
    from app.services.rag import _supported

    state = {"n": 0}

    class Fake(SourceConnector):
        def __init__(self, token=""): pass
        def validate_permissions(self): return {}
        def fetch_records(self, source_ref, cursor=None, since=None, until=None):
            state["n"] += 1
            body = "Decision: use Redis for the payments-service cache @gargi" if state["n"] == 1 else "Everything about caching was removed from this doc."
            return [NormalizedRecord("github", "pr1", "pull_request", "PR 1", body, "priyasharma", None, datetime(2026, 1, 2), source_ref),
                    NormalizedRecord("github", "c9", "commit", "x", "fix payments-service retry", "gargi", None, datetime(2026, 1, 3), source_ref)]

    monkeypatch.setattr(catalog, "get_connector", lambda name, token="", client=None: Fake(token))
    a = register(client, "f@x.io", "F")
    org, pid, t = a["org_id"], a["project_id"], a["token"]
    iid = client.post(f"/api/orgs/{org}/integrations", json={"connector": "github", "token": "tok", "consent": True}, headers=H(t)).json()["id"]
    sid = client.post(f"/api/projects/{pid}/sources", json={"integration_id": iid, "source_ref": "a/b"}, headers=H(t)).json()["id"]
    assert client.put(f"/api/projects/{pid}/consent-mode", json={"mode": "bogus"}, headers=H(t)).status_code == 422
    client.put(f"/api/projects/{pid}/consent-mode", json={"mode": "opt_in"}, headers=H(t))
    client.put(f"/api/projects/{pid}/consents", json={"author": "gargi", "granted": True}, headers=H(t))
    assert client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()["stored"] == 1  # only gargi said yes
    client.put(f"/api/projects/{pid}/consents", json={"author": "priyasharma", "granted": True}, headers=H(t))
    j = client.post(f"/api/projects/{pid}/sources/{sid}/sync", headers=H(t)).json()
    assert j["stored"] == 1 and j["duplicates"] == 1  # priya now consented; PR text changed so it is a new version
    g = client.get(f"/api/projects/{pid}/graph", headers=H(t)).json()
    assert "repository" in {n["type"] for n in g["nodes"]}
    cl = client.get(f"/api/projects/{pid}/claims", headers=H(t)).json()
    assert any(c["status"] == "outdated" for c in cl)  # the quoted text is gone from the newer source version
    # LLM answers must be supported sentence by sentence
    cites = [{"quote": "Redis was picked because refund lookups need fast reads"}]
    assert _supported("Redis was picked because refund lookups need fast reads [1].", cites)
    assert not _supported("Redis was picked and it handles 5000 users.", cites)


def test_reverify_flow(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    A, G = H(admin["token"]), H(gargi["token"])
    from app import db as dbm, models as m
    with dbm.SessionLocal() as db:
        c = m.Claim(project_id=pid, category="owner", subject_key="owner:x:priya", statement="Priya owns x", details={"needs_reverification": True, "source_changed": True},
                    status="verified", freshness="stale", created_by="system", verified_by=admin["user"]["id"])
        db.add(c)
        db.commit()
        cid = c.id
    assert cid in [x["id"] for x in client.get(f"/api/projects/{pid}/claims-needing-reverification", headers=A).json()]
    assert client.post(f"/api/projects/{pid}/claims/{cid}/reverify", headers=A).status_code == 403  # same person verified it
    assert client.post(f"/api/projects/{pid}/claims/{cid}/reverify", headers=G).status_code == 200
    got = client.get(f"/api/projects/{pid}/claims/{cid}", headers=A).json()
    assert got["freshness"] == "current" and "needs_reverification" not in got["details"] and got["details"]["reverified_by"] == gargi["user_id"]
    assert cid not in [x["id"] for x in client.get(f"/api/projects/{pid}/claims-needing-reverification", headers=A).json()]


def test_meeting_notes_participants_and_links(client):
    admin, priya, gargi, yen, org, pid = setup_team(client)
    notes = ("Meeting notes - payments sync\n"
             "Attendees: Priya Sharma, Gargi Yadav\n"
             "We decided to switch the payments-service cache to Redis because lookups are slow.\n"
             "Action item: update the payments-service runbook assigned to @gargi\n"
             "Who owns the invoice-worker retry policy?")
    r = up(client, admin["token"], pid, "payments-sync-notes.txt", notes, author="Priya Sharma")
    assert r.status_code == 201, r.text
    cl = client.get(f"/api/projects/{pid}/claims", headers=H(admin["token"])).json()
    cats = {(c["category"], c["statement"]) for c in cl}
    assert any(c["category"] == "attendance" and "Gargi Yadav" in c["statement"] for c in cl)
    assert any(c["category"] == "decision" and "Redis" in c["statement"] for c in cl)
    assert any(c["category"] == "task" and "runbook" in c["statement"] for c in cl)
    assert any(c["category"] == "question" for c in cl)
    recs = client.get(f"/api/projects/{pid}/records", headers=H(admin["token"])).json()
    assert recs[0]["record_type"] == "meeting"
    g = client.get(f"/api/projects/{pid}/graph", headers=H(admin["token"])).json()
    etypes = {e["relation"] for e in g["edges"]}
    assert "attended" in etypes and "decided_in" in etypes and "action_from" in etypes and "raised_in" in etypes
