"""SQL read-only enforcement — parse and block mutating queries."""
from __future__ import annotations

import sqlparse

from app.utils.errors import SecurityError

BLOCKED_TYPES = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "COMMIT", "ROLLBACK",
}

BLOCKED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "INTO",
}


def validate_read_only(sql: str) -> None:
    """Raise SecurityError if SQL contains mutation statements."""
    parsed = sqlparse.parse(sql)

    for statement in parsed:
        stmt_type = statement.get_type()
        if stmt_type and stmt_type.upper() in BLOCKED_TYPES:
            raise SecurityError(
                f"Write operations are not allowed. Blocked: {stmt_type}. "
                "Only SELECT queries are permitted."
            )

        # Extra safety: check for blocked keywords in the first few tokens
        tokens = [t.ttype and t.value.upper() for t in statement.tokens if not t.is_whitespace]
        first_keyword = None
        for t in statement.tokens:
            if t.ttype is sqlparse.tokens.Keyword.DML or t.ttype is sqlparse.tokens.Keyword.DDL:
                first_keyword = t.value.upper()
                break
            if t.ttype is sqlparse.tokens.Keyword and t.value.upper() in BLOCKED_KEYWORDS:
                first_keyword = t.value.upper()
                break

        if first_keyword and first_keyword in BLOCKED_KEYWORDS:
            raise SecurityError(
                f"Write operations are not allowed. Found: {first_keyword}. "
                "Only SELECT queries are permitted."
            )
