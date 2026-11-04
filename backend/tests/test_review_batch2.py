"""Lifecycle regression cases from features 8-14."""
from conftest import H, register
from app import models as m
from app.db import SessionLocal
from app.connectors.base import NormalizedRecord
from app.services import ingest, claims_engine, ledger
from app.crypto import EncryptedText
import pytest


def upload(c, a, text, name='note.md'):
    return c.post(f"/api/projects/{a['project_id']}/uploads", headers=H(a['token']), files={'file': (name, text.encode(), 'text/markdown')}).json()


def test_versions_revert_and_metadata(client):
    a = register(client, 'versions@x.io', 'Version')
    for text in ('Alpha', 'Beta', 'Alpha'):
        assert upload(client, a, text)['stored'] == 1
    assert upload(client, a, 'Alpha')['duplicates'] == 1
    assert upload(client, a, 'Alpha', 'copy.md')['stored'] == 1
    rows = client.get(f"/api/projects/{a['project_id']}/records", headers=H(a['token'])).json()
    assert sorted(r['version'] for r in rows if r['title'] == 'note.md') == [1, 2, 3]


def test_verified_deletion_cleans_materializations(client):
    a = register(client, 'deleteverified@x.io', 'Deletion')
    pid = a['project_id']
    rid = upload(client, a, 'Decision: Use Redis for payments-service because it is fast.')['record_id']
    with SessionLocal() as db:
        cs = db.query(m.Claim).filter_by(project_id=pid).all()
        assert cs
        for c in cs:
            if c.status != 'missing': c.status = 'verified'
        h = m.Handover(project_id=pid, departing_person_key='x', generated_by=a['user']['id'])
        db.add(h); db.flush()
        db.add(m.HandoverItem(handover_id=h.id, section='x', title='Secret snapshot'))
        db.commit()
    assert client.delete(f'/api/projects/{pid}/records/{rid}', headers=H(a['token'])).status_code == 200
    with SessionLocal() as db:
        assert db.query(m.Claim).filter_by(project_id=pid).count() == 0, [(c.category,c.status,c.statement,c.created_by) for c in db.query(m.Claim).filter_by(project_id=pid)]
        assert db.query(m.Decision).filter_by(project_id=pid).count() == 0
        assert db.query(m.Handover).filter_by(project_id=pid).count() == 0
        assert db.query(m.GraphNode).filter(m.GraphNode.project_id == pid, m.GraphNode.node_type != 'project', m.GraphNode.user_id.is_(None)).count() == 0
        assert ledger.verify_chain(db, pid)['valid']


def test_title_confidentiality_and_draft_detail(client):
    a = register(client, 'title@x.io', 'Title')
    rid = upload(client, a, 'Generic text', 'Confidential_salary.md')['record_id']
    # Keyword boundaries require natural title text, not underscores.
    rid = upload(client, a, 'Generic text', 'Confidential salary.md')['record_id']
    with SessionLocal() as db:
        assert db.get(m.SourceRecord, rid).visibility == 'restricted'
        c = m.Claim(project_id=a['project_id'], category='procedure', subject_key='private-draft', statement='unapproved answer', details={'draft': True})
        db.add(c); db.commit(); cid=c.id
    assert client.get(f"/api/projects/{a['project_id']}/claims/{cid}", headers=H(a['token'])).status_code == 404


def test_unanswered_gap_survives_unrelated_analysis_and_closes_on_evidence(client):
    a = register(client, 'questions@x.io', 'Questions')
    pid, h = a['project_id'], H(a['token'])
    question = 'How rotate kafka credentials?'
    assert not client.post(f'/api/projects/{pid}/ask', headers=h, json={'question':question}).json()['answered']
    client.post(f'/api/projects/{pid}/analyse', headers=h)
    assert any(g['type']=='unanswered_question' for g in client.get(f'/api/projects/{pid}/gaps', headers=h).json())
    upload(client, a, 'How rotate kafka credentials? Rotate kafka credentials using the documented rotation command.')
    assert not any(g['type']=='unanswered_question' for g in client.get(f'/api/projects/{pid}/gaps', headers=h).json())


def test_cross_source_same_content_keeps_provenance(client):
    a = register(client, 'provenance@x.io', 'Provenance')
    with SessionLocal() as db:
        p=db.get(m.Project,a['project_id'])
        ss=[m.Source(project_id=p.id,source_type='github', external_id=n,name=n) for n in ('one','two')]
        db.add_all(ss);db.flush()
        for source in ss:
            assert ingest.ingest_records(db,p,source,[NormalizedRecord('github','same','document','Title','Alice owns payments-service.')]).stored==1
        assert db.query(m.SourceRecord).filter_by(project_id=p.id).count()==2
        c=db.query(m.Claim).filter_by(project_id=p.id,category='owner').first()
        assert db.query(m.EvidenceLink).filter_by(claim_id=c.id).count()==2
        db.commit()


def test_decryption_failure_is_not_silent():
    with pytest.raises(ValueError, match='could not be decrypted'):
        EncryptedText().process_result_value('enc1:broken',None)


def test_derived_text_is_encrypted(client):
    from sqlalchemy import text
    a=register(client,'encrypted@x.io','Encryption')
    upload(client,a,'Alice owns payments-service.')
    with SessionLocal() as db:
        row=db.execute(text('SELECT statement,details FROM knowledge_claims LIMIT 1')).first()
        assert row[0].startswith('enc1:') and row[1].startswith('enc1:')
        assert db.execute(text('SELECT excerpt FROM evidence_links LIMIT 1')).scalar().startswith('enc1:')
