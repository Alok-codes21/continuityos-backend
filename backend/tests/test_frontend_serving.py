"""The combined app serves Vite assets without importing or replacing Flask."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.frontend import mount_frontend


def test_mount_built_frontend_after_api_routes(tmp_path, monkeypatch):
    (tmp_path / 'index.html').write_text('<html><body>Live workspace</body></html>')
    (tmp_path / 'asset.js').write_text('console.log("live")')
    monkeypatch.setenv('FRONTEND_DIST', str(tmp_path))
    app = FastAPI()

    @app.get('/api/health')
    def health():
        return {'ok': True}

    mount_frontend(app)
    client = TestClient(app)
    assert client.get('/').text == '<html><body>Live workspace</body></html>'
    assert client.get('/asset.js').status_code == 200
    assert client.get('/api/health').json() == {'ok': True}
    assert client.get('/api/missing').status_code == 404


def test_missing_build_keeps_api_available(tmp_path, monkeypatch):
    monkeypatch.setenv('FRONTEND_DIST', str(tmp_path / 'missing'))
    app = FastAPI()
    mount_frontend(app)
    assert TestClient(app).get('/').status_code == 404


def test_project_members_are_live_and_permission_scoped(client):
    from conftest import H, register
    admin = register(client, 'members@example.com', 'Members Admin')
    base = f"/api/projects/{admin['project_id']}/members"
    assert client.get(base, headers=H(admin['token'])).json() == []
    assert client.post(base, headers=H(admin['token']), json={'user_id': admin['user']['id']}).status_code == 201
    assert client.get(base, headers=H(admin['token'])).json()[0]['name'] == 'Members Admin'
    assert client.get('/api/projects', headers=H(admin['token'])).json()[0]['consent_mode'] == 'opt_out'
