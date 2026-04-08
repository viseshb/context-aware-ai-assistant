"""PII detection and redaction using regex patterns.

Uses regex-based detection for common PII types to avoid heavy presidio dependency
during initial development. Can be upgraded to presidio later for more comprehensive detection.
"""
from __future__ import annotations

import re

from app.utils.logging import get_logger

log = get_logger("security.pii")

# PII and secret-like patterns
PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("EMAIL", "[EMAIL_REDACTED]", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("PHONE", "[PHONE_REDACTED]", re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")),
    ("SSN", "[SSN_REDACTED]", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", "[CARD_REDACTED]", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("IP_ADDRESS", "[IP_REDACTED]", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("GITHUB_TOKEN", "[GITHUB_TOKEN_REDACTED]", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
    ("GITHUB_PAT", "[GITHUB_TOKEN_REDACTED]", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b")),
    ("SLACK_TOKEN", "[SLACK_TOKEN_REDACTED]", re.compile(r"\bxox(?:a|b|p|r|s|t)-[A-Za-z0-9-]{10,}\b")),
    ("AWS_ACCESS_KEY", "[AWS_KEY_REDACTED]", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("JWT", "[JWT_REDACTED]", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "PRIVATE_KEY",
        "[PRIVATE_KEY_REDACTED]",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.MULTILINE,
        ),
    ),
    (
        "CONNECTION_URI",
        "[CONNECTION_URI_REDACTED]",
        re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp):\/\/[^\s\"']+\b", re.IGNORECASE),
    ),
    (
        "SECRET_ASSIGNMENT",
        "[SECRET_ASSIGNMENT_REDACTED]",
        re.compile(
            r"(?im)^\s*(?:export\s+)?[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|ACCESS_KEY)[A-Z0-9_]*\s*=\s*.+$"
        ),
    ),
    (
        "API_KEY",
        "[KEY_REDACTED]",
        re.compile(r"\b(?:sk|pk|api|key|token|secret|password)[-_]?[a-zA-Z0-9]{20,}\b", re.IGNORECASE),
    ),
]


class PIIFilter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._redaction_count = 0

    def scan_and_redact(self, text: str) -> tuple[str, list[dict]]:
        """Scan text for PII and redact. Returns (redacted_text, redaction_events)."""
        if not self.enabled or not text:
            return text, []

        redactions: list[dict] = []
        result = text

        for pii_type, replacement, pattern in PATTERNS:
            result, count = pattern.subn(replacement, result)
            if count:
                self._redaction_count += count
                redactions.append({
                    "type": pii_type,
                    "replacement": replacement,
                    "count": count,
                })

        if redactions:
            log.warning(
                "pii_redacted",
                types=[r["type"] for r in redactions],
                total_redactions=sum(r["count"] for r in redactions),
            )

        return result, redactions

    @property
    def total_redactions(self) -> int:
        return self._redaction_count


# Singleton
pii_filter = PIIFilter()
