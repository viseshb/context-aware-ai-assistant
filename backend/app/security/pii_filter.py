"""PII detection and redaction using regex patterns.

Uses regex-based detection for common PII types to avoid heavy presidio dependency
during initial development. Can be upgraded to presidio later for more comprehensive detection.
"""
from __future__ import annotations

import re

from app.utils.logging import get_logger

log = get_logger("security.pii")

# PII patterns
PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("EMAIL", "[EMAIL_REDACTED]", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("PHONE", "[PHONE_REDACTED]", re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")),
    ("SSN", "[SSN_REDACTED]", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CREDIT_CARD", "[CARD_REDACTED]", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("IP_ADDRESS", "[IP_REDACTED]", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("API_KEY", "[KEY_REDACTED]", re.compile(r"\b(?:sk|pk|api|key|token|secret|password)[-_]?[a-zA-Z0-9]{20,}\b", re.IGNORECASE)),
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
            matches = pattern.findall(result)
            if matches:
                for match in matches:
                    result = result.replace(match, replacement)
                    self._redaction_count += 1
                    redactions.append({
                        "type": pii_type,
                        "replacement": replacement,
                        "count": len(matches),
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
