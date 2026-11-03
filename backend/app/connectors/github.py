"""Real GitHub REST connector (read-only): commits, pull requests, issues, CODEOWNERS."""
import base64
import fnmatch
from urllib.parse import quote
from pathlib import PurePosixPath
from datetime import datetime

import httpx

from .base import (ConnectorError, ConnectorForbidden, ConnectorRateLimited, NormalizedRecord, SourceConnector)

API = "https://api.github.com"


def _dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)


class GitHubConnector(SourceConnector):
    name = "github"
    max_pages = None  # defaults to settings.github_max_pages
    per_page = 50

    def __init__(self, token: str = "", client: httpx.Client = None):
        self.token = token
        self.client = client or httpx.Client(timeout=20)
        self.warnings = []
        self.truncated = False
        self.allowed_types = None
        self.file_paths = []
        self.max_files = 40
        self.max_file_bytes = 200_000
        self.max_total_bytes = 2_000_000

    def authenticate(self, credentials):
        self.token = credentials.get("token", "")
        return bool(self.token)

    def _get(self, path, params=None):
        r = self.client.get(API + path, params=params, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if r.status_code in (403, 429) and (r.headers.get("x-ratelimit-remaining") == "0" or r.status_code == 429):
            raise ConnectorRateLimited(int(r.headers.get("retry-after", "60")))
        if r.status_code == 401:
            raise ConnectorError("GitHub rejected the token")
        if r.status_code == 404:
            raise ConnectorError("Not found or token has no access")
        if r.status_code == 403:
            raise ConnectorForbidden("Token lacks permission for this resource")
        if r.status_code >= 400:
            raise ConnectorError(f"GitHub error {r.status_code}")
        return r.json()

    def validate_permissions(self):
        u = self._get("/user")
        return {"login": u.get("login"), "scopes": ["read:repo"]}

    def get_available_sources(self):
        repos = self._get("/user/repos", {"per_page": 50, "sort": "updated"})
        return [{"source_ref": r["full_name"], "name": r["full_name"], "private": r.get("private", False)} for r in repos]

    def _paged(self, path, params):
        from ..config import settings
        limit = self.max_pages or settings.github_max_pages
        out = []
        for page in range(1, limit + 1):
            data = self._get(path, {**params, "per_page": self.per_page, "page": page})
            out.extend(data)
            if len(data) < self.per_page:
                break
        else:
            self.truncated = True
            self.warnings.append(f"{path.rsplit('/', 1)[-1]}: stopped after {limit} pages, more records exist")
        return out

    def fetch_records(self, source_ref, cursor=None, since=None, until=None):
        if not since and cursor:  # incremental sync: the cursor is the time of the last successful sync
            try:
                since = datetime.fromisoformat(str(cursor))
            except ValueError:
                since = None
        p = {"since": since.isoformat() + "Z"} if since else {}
        recs = []
        self.warnings, self.truncated = [], False
        for kind, path, params in (("commit", "commits", p), ("pull_request", "pulls", {"state": "all", "sort": "updated", "direction": "desc"}), ("issue", "issues", {"state": "all", **p})):
            if self.allowed_types is not None and kind not in self.allowed_types:
                continue
            try:
                items = self._paged(f"/repos/{source_ref}/{path}", params)
            except ConnectorForbidden:
                self.warnings.append(f"{path}: token has no permission, skipped")
                continue
            for it in items:
                if kind == "pull_request" and since and (_dt(it.get("updated_at")) or datetime.max) < since:
                    continue  # PRs have no `since` filter in the API; filter by last update
                if kind == "issue" and "pull_request" in it:
                    continue
                recs.append(self.normalize_record({"_k": kind, **it}, source_ref))
        for path in (("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS")
                     if self.allowed_types is None or "codeowners" in self.allowed_types else ()):
            try:
                f = self._get(f"/repos/{source_ref}/contents/{path}")
                text = base64.b64decode(f["content"]).decode("utf-8", "replace")
                recs.append(NormalizedRecord("github", f"{source_ref}:{path}", "codeowners", f"{path} ({source_ref})", text,
                                             None, f.get("html_url"), None, source_ref))
                break
            except ConnectorError:
                continue
        if self.file_paths and (self.allowed_types is None or {"document", "code_file"} & self.allowed_types):
            recs.extend(self._fetch_files(source_ref))
        recs = [r for r in recs if not until or not r.occurred_at or r.occurred_at <= until]
        return recs

    def _file_kind(self, path):
        p = PurePosixPath(path)
        if p.suffix.lower() in {".md", ".rst", ".txt"} and (p.name.lower().startswith("readme") or "docs" in p.parts):
            return "document"
        excluded = {"node_modules", ".git", ".venv", "venv", "vendor", "dist", "build", "__pycache__"}
        if any(part in excluded or part.startswith(".env") for part in p.parts):
            return None
        if p.suffix.lower() in {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb", ".rs", ".cs", ".c", ".h", ".cpp"}:
            return "code_file"
        return None

    def _fetch_files(self, source_ref):
        """Read explicitly selected text files at one pinned default-branch commit. Never execute repository content."""
        try:
            repo = self._get(f"/repos/{source_ref}")
            branch = quote(repo.get("default_branch") or "main", safe="")
            head = self._get(f"/repos/{source_ref}/commits/{branch}")
            ref = head["sha"]
            tree_sha = head["commit"]["tree"]["sha"]
            tree = self._get(f"/repos/{source_ref}/git/trees/{tree_sha}", {"recursive": "1"})
            if tree.get("truncated"):
                self.truncated = True
                self.warnings.append("Repository file tree is truncated; selection coverage is incomplete")
            items, total = [], 0
            for ent in sorted(tree.get("tree", []), key=lambda x: x.get("path", "")):
                path = ent.get("path", "")
                if ent.get("type") != "blob" or ent.get("mode") not in ("100644", "100755"):
                    continue  # no symlinks or submodules
                if not any(fnmatch.fnmatchcase(path, pat) for pat in self.file_paths):
                    continue
                kind = self._file_kind(path)
                if not kind or (self.allowed_types is not None and kind not in self.allowed_types):
                    continue
                if ent.get("size", 0) > self.max_file_bytes:
                    self.warnings.append(f"Skipped oversized file: {path}")
                    continue
                if len(items) >= self.max_files or total + ent.get("size", 0) > self.max_total_bytes:
                    self.truncated = True
                    self.warnings.append("Selected repository files exceed sync file/byte limits")
                    break
                data = self._get(f"/repos/{source_ref}/contents/{quote(path, safe='/')}", {"ref": ref})
                if data.get("encoding") != "base64" or data.get("type") != "file":
                    self.warnings.append(f"Skipped unsupported file response: {path}")
                    continue
                raw = base64.b64decode(data.get("content", ""))
                if len(raw) > self.max_file_bytes or total + len(raw) > self.max_total_bytes or b"\x00" in raw:
                    self.warnings.append(f"Skipped oversized or binary file: {path}")
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeError:
                    self.warnings.append(f"Skipped non-UTF-8 file: {path}")
                    continue
                total += len(raw)
                items.append(NormalizedRecord("github", f"{source_ref}:{path}", kind, path,
                    f"File: {path}\n{text}", None, data.get("html_url"),
                    _dt(head["commit"].get("committer", {}).get("date")), source_ref,
                    {"path": path, "repository": source_ref, "blob_sha": ent.get("sha"), "commit_sha": ref}))
            return items
        except ConnectorRateLimited:
            raise
        except (ConnectorError, KeyError, ValueError) as e:
            self.warnings.append("Repository file fetch incomplete: " + str(e)[:150])
            self.truncated = True
            return []

    def normalize_record(self, raw, source_ref=""):
        k = raw["_k"]
        if k == "commit":
            c = raw.get("commit", {})
            author = (raw.get("author") or {}).get("login") or c.get("author", {}).get("name")
            msg = c.get("message", "")
            return NormalizedRecord("github", f"{source_ref}@{raw['sha'][:10]}", "commit", msg.split("\n")[0][:200], msg, author,
                                    raw.get("html_url"), _dt(c.get("author", {}).get("date")), source_ref)
        if k == "pull_request":
            body = raw.get("body") or ""
            return NormalizedRecord("github", f"{source_ref}#PR{raw['number']}", "pull_request", f"PR #{raw['number']}: {raw['title']}",
                                    f"{raw['title']}\n{body}", (raw.get("user") or {}).get("login"), raw.get("html_url"),
                                    _dt(raw.get("merged_at") or raw.get("created_at")), source_ref,
                                    {"state": raw.get("state"), "merged": bool(raw.get("merged_at")),
                                     "reviewers": [r.get("login") for r in raw.get("requested_reviewers", [])]})
        body = raw.get("body") or ""
        labels = [l.get("name") for l in raw.get("labels", [])]
        return NormalizedRecord("github", f"{source_ref}#{raw['number']}", "issue", f"Issue #{raw['number']}: {raw['title']}",
                                f"{raw['title']}\n{body}", (raw.get("user") or {}).get("login"), raw.get("html_url"),
                                _dt(raw.get("created_at")), source_ref,
                                {"state": raw.get("state"), "labels": labels, "assignees": [a.get("login") for a in raw.get("assignees", [])]})

    def revoke_access(self):
        self.token = ""
