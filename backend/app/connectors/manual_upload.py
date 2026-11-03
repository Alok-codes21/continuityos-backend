"""Built-in file upload connector: PDF, DOCX, TXT/MD, CSV."""
import csv
import io
import os

from .base import ConnectorError, NormalizedRecord, SourceConnector

ALLOWED = {".pdf", ".docx", ".txt", ".md", ".csv"}
MAX_BYTES = 10 * 1024 * 1024


def extract_text(filename: str, data: bytes) -> str:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED:
        raise ConnectorError(f"Unsupported file type '{ext}'. Allowed: PDF, DOCX, TXT, MD, CSV")
    if len(data) > MAX_BYTES:
        raise ConnectorError("File too large (10 MB max)")
    if ext == ".pdf":
        import fitz  # PyMuPDF
        try:
            doc = fitz.open(stream=data, filetype="pdf")
        except Exception:
            raise ConnectorError("Could not read PDF")
        return "\n".join(f"[page {i + 1}] " + p.get_text() for i, p in enumerate(doc))
    if ext == ".docx":
        import docx
        try:
            d = docx.Document(io.BytesIO(data))
        except Exception:
            raise ConnectorError("Could not read DOCX")
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    text = data.decode("utf-8", "replace")
    if ext == ".csv":
        rows = list(csv.reader(io.StringIO(text)))
        return "\n".join(" | ".join(r) for r in rows)
    return text


class ManualUploadConnector(SourceConnector):
    name = "manual_upload"

    def authenticate(self, credentials): return True
    def validate_permissions(self): return {"scopes": ["upload"]}
    def get_available_sources(self): return [{"source_ref": "uploads", "name": "File uploads"}]
    def fetch_records(self, source_ref, cursor=None, since=None, until=None): return []
    def revoke_access(self): return None

    def normalize_record(self, raw, source_ref="uploads"):
        import re
        rt = "meeting" if re.search(r"(?i)\b(attendees\s*:|meeting notes|minutes of|standup|weekly sync|1:1\b)",
                                    raw["filename"] + "\n" + (raw["text"] or "")[:600]) else "document"
        return NormalizedRecord("manual_upload", raw["filename"], rt, raw["filename"], raw["text"], raw.get("author"),
                                None, raw.get("occurred_at"), source_ref)
