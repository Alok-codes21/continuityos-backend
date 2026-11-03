"""Google Drive / Docs connector (read-only, drive.readonly scope). Reads only the selected folder; Google Docs are exported as text."""
from datetime import datetime

import httpx

from .base import ConnectorError, ConnectorForbidden, ConnectorRateLimited, NormalizedRecord, SourceConnector

API = "https://www.googleapis.com/drive/v3"
DOC = "application/vnd.google-apps.document"
FOLDER = "application/vnd.google-apps.folder"
MAX_CHARS = 200_000


def _dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None) if s else None


class GoogleDriveConnector(SourceConnector):
    name = "google_drive"
    max_files = 100

    def __init__(self, token: str = "", client: httpx.Client = None):
        self.token = token  # OAuth access token with the drive.readonly scope
        self.client = client or httpx.Client(timeout=30)
        self.warnings = []

    def authenticate(self, credentials):
        self.token = credentials.get("token", "")
        return bool(self.token)

    def _get(self, path, params=None, text=False):
        r = self.client.get(API + path, params=params, headers={"Authorization": f"Bearer {self.token}"})
        if r.status_code == 429:
            raise ConnectorRateLimited(int(r.headers.get("retry-after", "30")))
        if r.status_code == 401:
            raise ConnectorError("Google rejected the token")
        if r.status_code == 403:
            raise ConnectorForbidden("Token lacks permission for this resource")
        if r.status_code == 404:
            raise ConnectorError("Not found or token has no access")
        if r.status_code >= 400:
            raise ConnectorError(f"Google Drive error {r.status_code}")
        return r.text if text else r.json()

    def validate_permissions(self):
        d = self._get("/about", {"fields": "user(displayName,emailAddress)"})
        return {"user": (d.get("user") or {}).get("emailAddress"), "scopes": ["drive.readonly"]}

    def get_available_sources(self):
        d = self._get("/files", {"q": f"mimeType='{FOLDER}' and trashed=false", "fields": "files(id,name)", "pageSize": 100})
        return [{"source_ref": f["id"], "name": f["name"], "private": True} for f in d.get("files", [])]

    def fetch_records(self, source_ref, cursor=None, since=None, until=None):
        q = f"'{source_ref}' in parents and trashed=false and (mimeType='{DOC}' or mimeType='text/plain')"
        if since:
            q += f" and modifiedTime > '{since.isoformat()}Z'"
        files, token = [], None
        for _ in range(5):
            params = {"q": q, "fields": "nextPageToken,files(id,name,mimeType,modifiedTime,webViewLink,owners(displayName))", "pageSize": self.max_files}
            if token:
                params["pageToken"] = token
            d = self._get("/files", params)
            files.extend(d.get("files", []))
            token = d.get("nextPageToken")
            if not token or len(files) >= self.max_files:
                break
        d = {"files": files[: self.max_files]}
        recs, self.warnings = [], []
        for f in d.get("files", []):
            try:
                if f["mimeType"] == DOC:
                    body = self._get(f"/files/{f['id']}/export", {"mimeType": "text/plain"}, text=True)
                else:
                    body = self._get(f"/files/{f['id']}", {"alt": "media"}, text=True)
            except ConnectorForbidden:
                self.warnings.append(f"{f.get('name')}: no permission, skipped")
                continue
            if body.strip():
                recs.append(self.normalize_record({**f, "_text": body[:MAX_CHARS]}, source_ref))
        return [r for r in recs if not until or not r.occurred_at or r.occurred_at <= until]

    def normalize_record(self, raw, source_ref=""):
        owners = raw.get("owners") or [{}]
        return NormalizedRecord("google_drive", raw["id"], "document", raw.get("name", raw["id"])[:200], raw["_text"], owners[0].get("displayName"),
                                raw.get("webViewLink"), _dt(raw.get("modifiedTime")), source_ref, {"mime": raw.get("mimeType")})

    def revoke_access(self):
        self.token = ""
