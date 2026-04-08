"""PostgreSQL MCP server with read-only tools and settings-backed connection."""
from __future__ import annotations

import json
import logging

import asyncpg
from mcp.server.fastmcp import FastMCP

from app.config import settings

mcp = FastMCP("postgres")
logger = logging.getLogger("mcp.postgres")

_pool: asyncpg.Pool | None = None
_pool_dsn: str | None = None


async def _get_pool() -> asyncpg.Pool:
    global _pool, _pool_dsn

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    if _pool is None or _pool_dsn != settings.database_url:
        try:
            _pool = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=5)
            _pool_dsn = settings.database_url
            logger.info("postgres_pool_created")
        except Exception as e:
            logger.error("postgres_pool_failed error=%s", str(e))
            raise
    return _pool


@mcp.tool()
async def db_list_tables() -> str:
    """List all tables in the database with column counts."""
    logger.info("db_list_tables")
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT schemaname, tablename,
                       (SELECT count(*) FROM information_schema.columns
                        WHERE table_schema = t.schemaname AND table_name = t.tablename) as column_count
                FROM pg_catalog.pg_tables t
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename
                """
            )
            tables = [{"schema": row["schemaname"], "table": row["tablename"], "columns": row["column_count"]} for row in rows]
            logger.info("db_list_tables_result count=%d", len(tables))
            return json.dumps(tables, indent=2)
    except Exception as e:
        logger.error("db_list_tables_error error=%s", str(e))
        return json.dumps({"error": f"Failed to list tables: {e}"})


@mcp.tool()
async def db_get_schema(table: str) -> str:
    """Get the schema (columns, types, constraints) for a table."""
    logger.info("db_get_schema table=%s", table)
    parts = table.split(".")
    schema = parts[0] if len(parts) > 1 else "public"
    tbl = parts[-1]

    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            cols = await conn.fetch(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
                """,
                schema,
                tbl,
            )
            if not cols:
                logger.warning("db_get_schema_empty table=%s", table)
                return json.dumps({"error": f"Table '{table}' not found or has no columns"})
            columns = [
                {
                    "name": col["column_name"],
                    "type": col["data_type"],
                    "nullable": col["is_nullable"] == "YES",
                    "default": col["column_default"],
                }
                for col in cols
            ]
            logger.info("db_get_schema_result table=%s columns=%d", table, len(columns))
            return json.dumps({"table": table, "columns": columns}, indent=2)
    except Exception as e:
        logger.error("db_get_schema_error table=%s error=%s", table, str(e))
        return json.dumps({"error": f"Failed to get schema: {e}"})


@mcp.tool()
async def db_query(sql: str, params: str = "[]") -> str:
    """Execute a read-only SQL query (SELECT only)."""
    logger.info("db_query sql=%s", sql[:100])

    try:
        import sqlparse

        parsed = sqlparse.parse(sql)
        for stmt in parsed:
            stmt_type = stmt.get_type()
            if stmt_type and stmt_type.upper() not in ("SELECT", "UNKNOWN"):
                logger.warning("db_query_blocked type=%s sql=%s", stmt_type, sql[:100])
                return json.dumps({"error": f"Only SELECT queries allowed. Blocked: {stmt_type}"})
    except Exception as e:
        logger.error("db_query_parse_error error=%s", str(e))
        return json.dumps({"error": f"SQL parse error: {e}"})

    try:
        param_list = json.loads(params) if params != "[]" else []
    except json.JSONDecodeError as e:
        logger.error("db_query_params_error error=%s", str(e))
        return json.dumps({"error": f"Invalid params JSON: {e}"})

    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(sql, *param_list)
                results = [dict(row) for row in rows]
                for row in results:
                    for key, value in row.items():
                        if not isinstance(value, (str, int, float, bool, type(None))):
                            row[key] = str(value)
                truncated = len(results) > 100
                if truncated:
                    results = results[:100]
                logger.info("db_query_result rows=%d truncated=%s", len(results), truncated)
                return json.dumps({"rows": results, "count": len(results), "truncated": truncated}, indent=2)
    except Exception as e:
        logger.error("db_query_error sql=%s error=%s", sql[:100], str(e))
        return json.dumps({"error": f"Query failed: {e}"})


@mcp.tool()
async def db_explain_query(sql: str) -> str:
    """Get the execution plan for a SQL query."""
    logger.info("db_explain sql=%s", sql[:100])
    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction(readonly=True):
                rows = await conn.fetch(f"EXPLAIN ANALYZE {sql}")
                return "\n".join(row[0] for row in rows)
    except Exception as e:
        logger.error("db_explain_error sql=%s error=%s", sql[:100], str(e))
        return json.dumps({"error": f"EXPLAIN failed: {e}"})


if __name__ == "__main__":
    mcp.run(transport="stdio")
