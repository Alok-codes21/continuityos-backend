"""Real Slack Web API connector (read-only). Uses a bot token; reads only channels the bot was invited to."""
from datetime import datetime, timezone

import httpx
import json

from .base import ConnectorError, ConnectorRateLimited, NormalizedRecord, SourceConnector

API = "https://slack.com/api"


class SlackConnector(SourceConnector):
    name = "slack"
    max_pages = 5
    per_page = 100

    def __init__(self, token: str = "", client: httpx.Client = None):
        self.token = token
        self.client = client or httpx.Client(timeout=20)
        self.warnings, self.truncated, self.next_cursor = [], False, None

    def authenticate(self, credentials):
        self.token = credentials.get("token", "")
        return bool(self.token)

    def _call(self, method, params=None):
        r = self.client.get(f"{API}/{method}", params=params, headers={"Authorization": f"Bearer {self.token}"})
        if r.status_code == 429:
            raise ConnectorRateLimited(int(r.headers.get("retry-after", "30")))
        if r.status_code >= 400:
            raise ConnectorError(f"Slack error {r.status_code}")
        data = r.json()
        if not data.get("ok"):
            err = data.get("error", "unknown_error")
            if err == "ratelimited":
                raise ConnectorRateLimited(int(r.headers.get("retry-after", "30")))
            raise ConnectorError(f"Slack rejected the request: {err}")
        return data

    def validate_permissions(self):
        d = self._call("auth.test")
        return {"team": d.get("team"), "user": d.get("user"), "scopes": ["channels:history", "channels:read"]}

    def get_available_sources(self):
        out, cursor = [], None
        for _ in range(20):
            p = {"types": "public_channel", "exclude_archived": "true", "limit": 200}
            if cursor:
                p["cursor"] = cursor
            d = self._call("conversations.list", p)
            out.extend({"source_ref": c["id"], "name": "#" + c.get("name", c["id"]), "private": False}
                       for c in d.get("channels", []) if c.get("is_member") and not c.get("is_archived") and not c.get("is_private"))
            cursor = (d.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
        if cursor:
            self.warnings.append("Channel discovery capped; additional channels may exist")
        return out

    def fetch_records(self, source_ref, cursor=None, since=None, until=None):
        self.warnings, self.truncated, self.next_cursor = [], False, None
        state = {}
        try:
            state = json.loads(cursor) if cursor and cursor.startswith("{") else {}
        except ValueError:
            pass
        params = {"channel": source_ref, "limit": self.per_page}
        if since:
            params["oldest"] = str(since.replace(tzinfo=timezone.utc).timestamp())
        if until:
            params["latest"] = str(until.replace(tzinfo=timezone.utc).timestamp())
        recs, next_page = [], state.get("history")
        pending = list(state.get("threads") or [])
        # Continue previously capped thread pages before advancing history.
        for thread in pending:
            recs.extend(self._replies(source_ref, thread["ts"], thread.get("cursor")))
        for _ in range(self.max_pages):
            if next_page:
                params["cursor"] = next_page
            d = self._call("conversations.history", params)
            for msg in d.get("messages", []):
                if msg.get("type") == "message" and not msg.get("subtype") and msg.get("text"):
                    recs.append(self.normalize_record(msg, source_ref))
                    if msg.get("reply_count"):
                        recs.extend(self._replies(source_ref, msg["ts"]))
            next_page = (d.get("response_metadata") or {}).get("next_cursor")
            if not next_page:
                break
        threads = getattr(self, "_pending_threads", [])
        if next_page or threads:
            self.truncated = True
            self.warnings.append("Slack sync capped; continuation saved")
            self.next_cursor = json.dumps({"history": next_page, "threads": threads})
        self._pending_threads = []
        return recs

    def _replies(self, channel, thread_ts, cursor=None):
        out = []
        for _ in range(self.max_pages):
            params = {"channel": channel, "ts": thread_ts, "limit": self.per_page}
            if cursor:
                params["cursor"] = cursor
            d = self._call("conversations.replies", params)
            out.extend(self.normalize_record({**r, "thread_ts": thread_ts}, channel) for r in d.get("messages", [])
                       if r.get("ts") != thread_ts and not r.get("subtype") and r.get("text"))
            cursor = (d.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break
        if cursor:
            self._pending_threads = getattr(self, "_pending_threads", []) + [{"ts": thread_ts, "cursor": cursor}]
        return out

    def normalize_record(self, raw, source_ref=""):
        ts = raw["ts"]
        text = raw.get("text", "")
        when = datetime.fromtimestamp(float(ts), tz=timezone.utc).replace(tzinfo=None)
        return NormalizedRecord("slack", f"{source_ref}:{ts}", "message", text.split("\n")[0][:120], text, raw.get("user"),
                                None, when, source_ref, {"thread_ts": raw.get("thread_ts") or (raw["ts"] if raw.get("reply_count") else None)})

    def revoke_access(self):
        try:
            self._call("auth.revoke")
        finally:
            self.token = ""
