"""Integration catalogue shown on the Integrations screen. `implemented` is the truth: nothing else is ever shown as connected."""
from .base import ConnectorUnavailable, SourceConnector
from .github import GitHubConnector
from .slack import SlackConnector
from .manual_upload import ManualUploadConnector

CATALOG = [
    {"id": "github", "name": "GitHub", "category": "development", "implemented": True, "note": "Repos, commits, PRs, issues, CODEOWNERS"},
    {"id": "gitlab", "name": "GitLab", "category": "development", "implemented": False, "note": "Coming soon"},
    {"id": "jira", "name": "Jira", "category": "development", "implemented": False, "note": "Coming soon"},
    {"id": "slack", "name": "Slack", "category": "communication", "implemented": True, "note": "Selected public channels the bot was invited to (read-only)"},
    {"id": "microsoft_teams", "name": "Microsoft Teams", "category": "communication", "implemented": False, "note": "Coming soon"},
    {"id": "twist", "name": "Twist", "category": "communication", "implemented": False, "note": "Coming soon"},
    {"id": "google_meet", "name": "Google Meet", "category": "meetings", "implemented": False, "note": "Authorised transcripts only"},
    {"id": "zoom", "name": "Zoom", "category": "meetings", "implemented": False, "note": "Authorised transcripts only"},
    {"id": "google_drive", "name": "Google Drive", "category": "documents", "implemented": False, "note": "Project folder scope - planned for phase 2"},
    {"id": "manual_upload", "name": "File upload", "category": "documents", "implemented": True, "builtin": True, "note": "PDF, DOCX, TXT, CSV"},
    {"id": "notion", "name": "Notion", "category": "documents", "implemented": False, "note": "Coming soon"},
]


def get_connector(name: str, token: str = "", client=None) -> SourceConnector:
    if name == "github":
        return GitHubConnector(token, client)
    if name == "slack":
        return SlackConnector(token, client)
    if name == "manual_upload":
        return ManualUploadConnector()
    raise ConnectorUnavailable(f"Connector '{name}' is not available yet")
