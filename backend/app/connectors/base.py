from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class ConnectorError(Exception):
    pass


class ConnectorUnavailable(ConnectorError):
    pass


class ConnectorRateLimited(ConnectorError):
    def __init__(self, retry_after=60):
        super().__init__(f"rate limited, retry after {retry_after}s")
        self.retry_after = retry_after


@dataclass
class NormalizedRecord:
    source_type: str
    external_id: str
    record_type: str  # commit | pull_request | issue | document | message | codeowners
    title: str
    content: str
    author: Optional[str] = None
    url: Optional[str] = None
    occurred_at: Optional[datetime] = None
    source_ref: str = ""
    meta: dict = field(default_factory=dict)


class SourceConnector:
    """Common interface (plan section 8.1). Every adapter implements all six methods."""
    name = "base"

    def authenticate(self, credentials: dict): raise NotImplementedError
    def validate_permissions(self) -> dict: raise NotImplementedError
    def get_available_sources(self) -> list: raise NotImplementedError
    def fetch_records(self, source_ref: str, cursor=None, since=None, until=None) -> list: raise NotImplementedError
    def normalize_record(self, raw: dict, source_ref: str = "") -> NormalizedRecord: raise NotImplementedError
    def revoke_access(self) -> None: raise NotImplementedError
