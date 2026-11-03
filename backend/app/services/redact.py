"""Secret/PII detection and prompt-injection flagging. Applied BEFORE anything is stored or embedded."""
import re

SECRET_PATTERNS = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)", re.S)),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe_key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("credential_assignment", re.compile(
        r"(?i)\b((?:api[_-]?key|secret|token|passwd|password|pwd|client[_-]?secret|access[_-]?key)\s*[:=]\s*)(['\"]?)([^\s'\"]{6,})\2")),
]
PII_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)\d{3,4}[\s-]?\d{3,4}(?!\w)")),
]
INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|prompts?|rules)"),
    re.compile(r"(?i)disregard (?:all |any |the )?(?:previous|prior|above|system) (?:instructions|prompts?|rules)"),
    re.compile(r"(?i)\b(?:reveal|print|dump|exfiltrate|send)\b.{0,60}\b(?:credentials?|passwords?|secrets?|api keys?|tokens?|system prompt)\b"),
    re.compile(r"(?i)\byou are now\b.{0,40}\b(?:admin|root|unrestricted|dan)\b"),
    re.compile(r"(?i)\bact as (?:the )?(?:system|administrator|root)\b"),
    re.compile(r"(?i)<\s*/?\s*system\s*>"),
]


def redact(text: str, redact_pii: bool = True):
    """Return (clean_text, findings). Findings never include the secret itself."""
    findings = []

    def sub(kind):
        def _r(mt):
            findings.append(kind)
            if kind == "credential_assignment":
                return f"{mt.group(1)}[REDACTED:secret]"
            return f"[REDACTED:{kind}]"
        return _r

    for kind, pat in SECRET_PATTERNS:
        text = pat.sub(sub(kind), text)
    if redact_pii:
        # only emails are masked by default; phone numbers are too noisy in commit/PR text
        for kind, pat in PII_PATTERNS[:1]:
            text = pat.sub(sub(kind), text)
    return text, findings


def looks_like_injection(text: str) -> bool:
    return any(p.search(text) for p in INJECTION_PATTERNS)
