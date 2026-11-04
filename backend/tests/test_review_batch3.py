"""Identity and approval isolation regressions from features 15-21."""
from conftest import H, register, add_member
from app import models as m
from app.db import SessionLocal
from app.services import graph
from test_flow import setup_team, load_docs


def test_names_do_not_bind_accounts_implicitly(client):
    a=register(client,'alice@x.io','Alice Smith')
    with SessionLocal() as db:
        person=graph.ensure_person(db,a['project_id'],'Alice Smith')
        assert person.user_id is None
        db.commit()
    assert client.post(f"/api/projects/{a['project_id']}/interviews", headers=H(a['token']), json={'person':'Alice Smith'}).status_code==409


def test_different_bound_accounts_cannot_merge(client):
    a=register(client,'bound@x.io','First Person')
    b=add_member(client,a,a['org_id'],'other@x.io','Other Person','contributor')
    with SessionLocal() as db:
        p=graph.ensure_person(db,a['project_id'],'First Person');p.user_id=a['user']['id']
        q=graph.ensure_person(db,a['project_id'],'Other Person');q.user_id=b['user_id'];db.commit()
    assert client.post(f"/api/projects/{a['project_id']}/graph/people/merge", headers=H(a['token']), json={'keep':'firstperson','merge':'otherperson'}).status_code==409


def test_confirmation_idempotent_and_pending_blocks_completion(client):
    admin,priya,gargi,_,_,pid=setup_team(client)
    load_docs(client,admin,pid)
    iv=client.post(f'/api/projects/{pid}/interviews',headers=H(gargi['token']),json={'person':'Priya Sharma'}).json()
    q=next(q for q in iv['questions'] if q['context']['gap_type']=='undocumented_decision')
    base=f"/api/projects/{pid}/interviews/{iv['id']}"
    response=client.post(f"{base}/questions/{q['id']}/answers",headers=H(priya['token']),json={'answer':'Redis was chosen because fast reads are needed.'}).json()['response_id']
    first=client.post(f'{base}/responses/{response}/confirm',headers=H(priya['token'])).json()['approval_id']
    assert client.post(f'{base}/responses/{response}/confirm',headers=H(priya['token'])).json()['approval_id']==first
    assert client.post(f'{base}/complete',headers=H(gargi['token'])).status_code==409
    assert client.post(f'/api/projects/{pid}/approvals/{first}/decide',headers=H(gargi['token']),json={'approve':True}).status_code==200
    assert client.post(f'{base}/responses/{response}/confirm',headers=H(priya['token'])).status_code==409


def test_unlinked_decision_not_in_overview(client):
    a=register(client,'orphan@x.io','Orphan')
    with SessionLocal() as db:
        db.add(m.Decision(project_id=a['project_id'],title='Private unlinked decision'));db.commit()
    assert not client.get(f"/api/projects/{a['project_id']}/overview",headers=H(a['token'])).json()['latest_decisions']


def test_correction_updates_structured_api_and_draft_progress(client):
    admin,priya,gargi,_,_,pid=setup_team(client)
    load_docs(client,admin,pid)
    cl=client.get(f'/api/projects/{pid}/claims?category=api',headers=H(priya['token'])).json()[0]
    ap=client.post(f"/api/projects/{pid}/claims/{cl['id']}/corrections",headers=H(priya['token']),json={'corrected_statement':'Endpoint GET /payments/refunds','reason':'Correct path'}).json()['approval_id']
    assert client.post(f'/api/projects/{pid}/approvals/{ap}/decide',headers=H(gargi['token']),json={'approve':True}).status_code==200
    detail=client.get(f"/api/projects/{pid}/claims/{cl['id']}",headers=H(admin['token'])).json()
    assert detail['details']['endpoint']=='GET /payments/refunds'
    assert detail['subject_key']=='api:GET /payments/refunds'
    assert detail['details']['verification_method']=='approved_correction'


def test_cross_interview_confirmation_is_rejected(client):
    admin,priya,gargi,_,_,pid=setup_team(client)
    load_docs(client,admin,pid)
    iv=client.post(f'/api/projects/{pid}/interviews',headers=H(gargi['token']),json={'person':'Priya Sharma'}).json()
    q=iv['questions'][0]
    base=f"/api/projects/{pid}/interviews/{iv['id']}"
    response=client.post(f"{base}/questions/{q['id']}/answers",headers=H(priya['token']),json={'answer':'An explicit employee answer.'}).json()['response_id']
    other=client.post(f'/api/projects/{pid}/interviews',headers=H(gargi['token']),json={'person':'Priya Sharma'}).json()
    assert client.post(f"/api/projects/{pid}/interviews/{other['id']}/responses/{response}/confirm",headers=H(priya['token'])).status_code==404


def test_selection_updates_target_exact_row_and_reject_other_source(client):
    a=register(client,'selection-review@x.io','Selection Review')
    pid=a['project_id']
    with SessionLocal() as db:
        integ=m.Integration(org_id=a['org_id'],connector='manual_upload',status='active',scopes={},created_by=a['user']['id'])
        db.add(integ);db.flush()
        source=m.Source(project_id=pid,integration_id=integ.id,source_type='manual_upload',external_id='one',name='One')
        db.add(source)
        first=m.SourceSelection(integration_id=integ.id,project_id=pid,source_ref='one',included=True)
        second=m.SourceSelection(integration_id=integ.id,project_id=pid,source_ref='one',included=True)
        other=m.SourceSelection(integration_id=integ.id,project_id=pid,source_ref='other',included=True)
        db.add_all([first,second,other]);db.commit()
        sid,first_id,second_id,other_id=source.id,first.id,second.id,other.id
    base=f'/api/projects/{pid}/sources/{sid}/selection'
    assert client.put(base,headers=H(a['token']),json={'selection_id':second_id,'included':False}).status_code==200
    assert client.put(base,headers=H(a['token']),json={'selection_id':other_id,'included':False}).status_code==404
    with SessionLocal() as db:
        assert db.get(m.SourceSelection,first_id).included is True
        assert db.get(m.SourceSelection,second_id).included is False
