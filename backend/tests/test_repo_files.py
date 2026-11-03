import base64
from datetime import datetime

import httpx

from app.connectors.github import GitHubConnector
from conftest import H, register


def file_connector(files):
    seen = []
    def handler(req):
        path = req.url.path
        seen.append((path, dict(req.url.params)))
        if path == '/repos/acme/pay':
            return httpx.Response(200, json={'default_branch': 'main'})
        if path.endswith('/commits/main'):
            return httpx.Response(200, json={'sha': 'pinned', 'commit': {'tree': {'sha': 'tree'}, 'committer': {'date': '2026-01-02T00:00:00Z'}}})
        if path.endswith('/git/trees/tree'):
            return httpx.Response(200, json={'tree': [{'path': f, 'type': 'blob', 'mode': '100644', 'size': len(t.encode()), 'sha': str(n)} for n, (f, t) in enumerate(files.items())]})
        if '/contents/' in path:
            name = path.split('/contents/')[1]
            if name in files:
                return httpx.Response(200, json={'type': 'file', 'encoding': 'base64', 'content': base64.b64encode(files[name].encode()).decode(), 'html_url': 'https://github.com/acme/pay/blob/pinned/' + name})
        return httpx.Response(404)
    return GitHubConnector('tok', httpx.Client(transport=httpx.MockTransport(handler))), seen


def test_selected_docs_only_and_pinned_version():
    c, seen = file_connector({'README.md': 'Priya owns payments-service.', 'docs/runbook.md': 'Run rollback.', 'private.txt': 'ignore', 'src/main.py': 'print(1)'})
    c.allowed_types, c.file_paths = {'document'}, ['README.md', 'docs/*', 'src/*']
    recs = c.fetch_records('acme/pay')
    assert {r.title for r in recs} == {'README.md', 'docs/runbook.md'}
    assert all(r.meta['commit_sha'] == 'pinned' and r.record_type == 'document' for r in recs)
    assert all(params.get('ref') == 'pinned' for path, params in seen if '/contents/' in path)
    assert not any(path.endswith('/issues') or path.endswith('/pulls') for path, _ in seen)


def test_docs_require_selection_scope_and_respect_limits():
    c, seen = file_connector({'README.md': 'abc', 'docs/a.md': 'a'*50})
    c.allowed_types = {'document'}
    assert c.fetch_records('acme/pay') == [] and seen == []
    c.file_paths, c.allowed_types = ['README.md'], set()
    assert c.fetch_records('acme/pay') == [] and seen == []
    c.file_paths, c.allowed_types, c.max_file_bytes = ['README.md', 'docs/*'], {'document'}, 10
    assert [r.title for r in c.fetch_records('acme/pay')] == ['README.md']
    assert any('oversized' in w for w in c.warnings)
    c, _ = file_connector({'README.md': 'abc', 'docs/a.md': 'def'})
    c.allowed_types, c.file_paths, c.max_files = {'document'}, ['*'], 1
    assert len(c.fetch_records('acme/pay')) == 1 and c.truncated


def test_docs_api_selection_versions_and_citations(client, monkeypatch):
    from app.connectors import catalog
    from app import db as dbm, models as m
    files = {'README.md': 'Priya owns payments-service.\nThe payments-service timeout is 30 seconds.'}
    connectors = []
    def factory(*a, **kw):
        c, _ = file_connector(files)
        c.validate_permissions = lambda: {}
        connectors.append(c)
        return c
    monkeypatch.setattr(catalog, 'get_connector', factory)
    a = register(client, 'files@x.io', 'Files')
    org, pid, h = a['org_id'], a['project_id'], H(a['token'])
    iid = client.post(f'/api/orgs/{org}/integrations', headers=h, json={'connector': 'github', 'token': 'tok', 'consent': True, 'scopes': {'permissions': ['documents']}}).json()['id']
    sid = client.post(f'/api/projects/{pid}/sources', headers=h, json={'integration_id': iid, 'source_ref': 'acme/pay', 'file_paths': ['README.md']}).json()['id']
    url = f'/api/projects/{pid}/sources/{sid}'
    assert client.post(url+'/sync', headers=h).json()['stored'] == 1
    assert client.post(url+'/sync', headers=h).json()['duplicates'] == 1
    files['README.md'] = 'Priya owns payments-service.\nThe payments-service timeout is 60 seconds.'
    assert client.post(url+'/sync', headers=h).json()['stored'] == 1
    recs = client.get(f'/api/projects/{pid}/records', headers=h).json()
    assert sorted(r['version'] for r in recs) == [1, 2]
    answer = client.post(f'/api/projects/{pid}/ask', headers=h, json={'question': 'Who owns payments?'}).json()
    assert answer['answered'] and answer['citations'][0]['record_id']
    assert client.put(url+'/selection', headers=h, json={'file_paths': ['../secrets']}).status_code == 422
    client.put(url+'/selection', headers=h, json={'included': False})
    assert client.post(url+'/sync', headers=h).json()['stored'] == 0
