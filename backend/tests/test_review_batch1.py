"""Regression cases from the detailed review of features 1-7."""
import json
from datetime import datetime, timezone
from types import SimpleNamespace as S

import httpx
import pytest

from conftest import H, register
from app.services.ingest import selection_allows
from app.connectors.slack import SlackConnector
from app.connectors.gdrive import GoogleDriveConnector


def test_date_bounds_exclude_undated_and_normalize_utc():
    sel = S(included=True, date_from=datetime(2026, 1, 1, tzinfo=timezone.utc), date_to=None, content_types=[])
    assert not selection_allows(S(occurred_at=None, record_type='document'), [sel])
    assert selection_allows(S(occurred_at=datetime(2026, 1, 1), record_type='document'), [sel])


def test_immediate_session_revocation_and_new_login(client):
    a = register(client, 'instant@x.io', 'Instant')
    h = H(a['token'])
    assert client.post('/api/auth/revoke-all-sessions', headers=h).status_code == 200
    assert client.get('/api/auth/me', headers=h).status_code == 401
    new = client.post('/api/auth/login', json={'email': 'instant@x.io', 'password': 'correct-horse-1'}).json()['token']
    assert client.get('/api/auth/me', headers=H(new)).status_code == 200


def test_slack_history_and_replies_continue_with_cursors():
    seen = []
    def h(req):
        params = dict(req.url.params)
        seen.append((req.url.path, params))
        if req.url.path.endswith('conversations.replies'):
            if params.get('cursor') == 'R2':
                return httpx.Response(200, json={'ok': True, 'messages': [{'ts': '3', 'user': 'b', 'text': 'reply 2'}]})
            return httpx.Response(200, json={'ok': True, 'messages': [{'ts': '2', 'user': 'a', 'text': 'reply'}], 'response_metadata': {'next_cursor': 'R2'}})
        if params.get('cursor') == 'H2':
            return httpx.Response(200, json={'ok': True, 'messages': []})
        return httpx.Response(200, json={'ok': True, 'messages': [{'type': 'message', 'ts': '1', 'user': 'a', 'text': 'root', 'reply_count': 2}], 'response_metadata': {'next_cursor': 'H2'}})
    c = SlackConnector('t', httpx.Client(transport=httpx.MockTransport(h)))
    c.max_pages = 1
    first = c.fetch_records('C')
    assert len(first) == 2 and c.truncated
    state = json.loads(c.next_cursor)
    assert state['history'] == 'H2' and state['threads'][0]['cursor'] == 'R2'
    second = c.fetch_records('C', cursor=c.next_cursor)
    assert any(r.content == 'reply 2' for r in second) and c.next_cursor is None


def test_drive_continuation_not_silently_dropped():
    def h(req):
        if req.url.params.get('alt') == 'media':
            return httpx.Response(200, text='file text')
        if req.url.params.get('pageToken'):
            return httpx.Response(200, json={'files': [{'id': '2', 'name': 'b', 'mimeType': 'text/plain'}]})
        return httpx.Response(200, json={'nextPageToken': 'P2', 'files': [{'id': '1', 'name': 'a', 'mimeType': 'text/plain'}]})
    c = GoogleDriveConnector('t', httpx.Client(transport=httpx.MockTransport(h)))
    c.max_files = 1
    assert c.fetch_records('F')[0].external_id == '1' and c.truncated
    assert c.fetch_records('F', cursor=c.next_cursor)[0].external_id == '2' and c.next_cursor is None


def test_upload_body_pdf_and_explicit_meeting_limits(client):
    a = register(client, 'uploadlimits@x.io', 'Upload')
    h, pid = H(a['token']), a['project_id']
    r = client.post(f'/api/projects/{pid}/uploads', headers=h, files={'file': ('notes.txt', b'plain notes', 'text/plain')}, data={'record_type': 'meeting'})
    assert r.status_code == 201
    assert client.get(f'/api/projects/{pid}/records', headers=h).json()[0]['record_type'] == 'meeting'
    assert client.post(f'/api/projects/{pid}/uploads', headers={**h, 'Content-Length': str(13*1024*1024)}, content=b'x').status_code == 413
    import fitz
    from app.connectors.manual_upload import extract_text
    from app.connectors.base import ConnectorError
    with fitz.open() as doc:
        for _ in range(301):
            doc.new_page()
        data = doc.tobytes()
    with pytest.raises(ConnectorError, match='300-page'):
        extract_text('huge.pdf', data)


def test_change_password_revokes_old_sessions(client):
    a = register(client, 'password@x.io', 'Password')
    r = client.post('/api/auth/change-password', headers=H(a['token']), json={'current_password': 'correct-horse-1', 'new_password': 'new-correct-horse-2'})
    assert r.status_code == 200
    assert client.get('/api/auth/me', headers=H(a['token'])).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'password@x.io', 'password': 'new-correct-horse-2'}).status_code == 200
