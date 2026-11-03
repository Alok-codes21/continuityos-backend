"""Handover audience, grounding, skills and production safeguards."""
from conftest import H, register
from app import models as m
from app.db import SessionLocal
from app.services import rag, llm
from test_flow import setup_team, load_docs, up


def test_handover_never_copies_restricted_manager_evidence(client):
    admin,priya,gargi,yen,_,pid=setup_team(client)
    load_docs(client,admin,pid)
    up(client,admin['token'],pid,'confidential.md','Decision: Payments-service uses secret-customer-platform because payroll is confidential.',visibility='restricted')
    h=client.post(f'/api/projects/{pid}/handovers',headers=H(gargi['token']),json={'person':'Priya Sharma','incoming_user_id':yen['user_id']}).json()
    assert 'secret-customer-platform' not in str(h)
    url=f"/api/projects/{pid}/handovers/{h['id']}/request-approval"
    ap=client.post(url,headers=H(gargi['token'])).json()['approval_id']
    assert client.post(url,headers=H(gargi['token'])).json()['approval_id']==ap
    assert client.post(f'/api/projects/{pid}/approvals/{ap}/decide',headers=H(admin['token']),json={'approve':True}).status_code==200
    assert client.get(f"/api/projects/{pid}/handovers/{h['id']}",headers=H(yen['token'])).status_code==200
    with SessionLocal() as db:
        db.query(m.ProjectMember).filter_by(project_id=pid,user_id=yen['user_id']).delete();db.commit()
    assert client.get(f"/api/projects/{pid}/handovers/{h['id']}",headers=H(yen['token'])).status_code==404


def test_polarity_and_strict_entailment(monkeypatch):
    monkeypatch.setattr(llm,'available',lambda:False)
    assert not rag._supported('Redis is not used for the payments cache [1].',[{'quote':'Redis is used for the payments cache.'}])
    monkeypatch.setattr(llm,'_rephrase_raw',lambda x:'YES, but the excerpt does not support the sentence')
    assert llm.entails('a','b') is None
    monkeypatch.setattr(llm,'_rephrase_raw',lambda x:'YES.')
    assert llm.entails('a','b') is True


def test_skill_target_must_be_member(client):
    a=register(client,'skillscope@x.io','Skill')
    assert client.post(f"/api/projects/{a['project_id']}/skills",headers=H(a['token']),json={'skill':'Python','user_id':'someone-else'}).status_code==404


def test_production_config_rejects_unsafe_defaults(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.delenv('JWT_SECRET',raising=False)
    import pytest
    with pytest.raises(ValueError,match='JWT_SECRET'): Settings()
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('JWT_HOURS','-1')
    with pytest.raises(ValueError,match='positive ranges'): Settings()


def test_readiness_is_separate(client):
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/ready').json()['status']=='ready'
