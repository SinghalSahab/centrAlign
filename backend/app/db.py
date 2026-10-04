import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import aiosqlite
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings

logger = logging.getLogger("db")

_pg_pool: Optional[AsyncConnectionPool] = None
_default_db_dir = Path(__file__).resolve().parent.parent / "data"
_default_db_dir.mkdir(parents=True, exist_ok=True)
_sqlite_path: str = str(_default_db_dir / "local.db")

def is_postgres() -> bool:

    url = settings.DATABASE_URL or ""
    return url.startswith("postgres://") or url.startswith("postgresql://")

def _normalize_sqlite_query(query: str) -> str:
    # Replace %s with ? for sqlite parameter binding
    # and handle RETURNING id for sqlite by rewriting if needed
    normalized = query.replace("%s", "?")
    return normalized

def _serialize_param(param: Any, to_sqlite: bool) -> Any:
    if to_sqlite:
        if isinstance(param, (dict, list)):
            return json.dumps(param)
        if isinstance(param, bool):
            return 1 if param else 0
    return param

def _deserialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    # Parse json fields if they are strings
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
            try:
                d[k] = json.loads(v)
            except Exception:
                pass
    return d

async def init_db():
    global _pg_pool, _sqlite_path
    if is_postgres():
        logger.info("Initializing Neon Postgres AsyncConnectionPool...")
        _pg_pool = AsyncConnectionPool(
            conninfo=settings.DATABASE_URL,
            min_size=1,
            max_size=10,
            open=False,
            kwargs={"autocommit": True, "row_factory": dict_row}
        )
        await _pg_pool.open()
        await run_migrations()
    else:
        logger.info("DATABASE_URL not set or not Postgres. Falling back to local SQLite DB.")
        db_dir = Path(__file__).resolve().parent.parent / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        _sqlite_path = str(db_dir / "local.db")
        await run_migrations()

async def close_db():
    global _pg_pool
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None

async def run_migrations():
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if is_postgres():
        sql_file = migrations_dir / "001_init.sql"
        sql = sql_file.read_text()
        async with _pg_pool.connection() as conn:
            await conn.execute(sql)
        logger.info("Postgres migration executed successfully.")
    else:
        sql_file = migrations_dir / "001_sqlite_init.sql"
        sql = sql_file.read_text()
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.executescript(sql)
            await db.commit()
        logger.info("SQLite migration executed successfully.")

async def execute(query: str, params: Union[tuple, list] = ()) -> None:
    if is_postgres():
        async with _pg_pool.connection() as conn:
            await conn.execute(query, params)
    else:
        q = _normalize_sqlite_query(query)
        p = [_serialize_param(x, to_sqlite=True) for x in params]
        async with aiosqlite.connect(_sqlite_path) as db:
            await db.execute(q, p)
            await db.commit()

async def fetch_one(query: str, params: Union[tuple, list] = ()) -> Optional[Dict[str, Any]]:
    if is_postgres():
        async with _pg_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                res = await cur.fetchone()
                return dict(res) if res else None
    else:
        q = _normalize_sqlite_query(query)
        p = [_serialize_param(x, to_sqlite=True) for x in params]
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(q, p) as cursor:
                row = await cursor.fetchone()
                return _deserialize_row(dict(row)) if row else None

async def fetch_all(query: str, params: Union[tuple, list] = ()) -> List[Dict[str, Any]]:
    if is_postgres():
        async with _pg_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, params)
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    else:
        q = _normalize_sqlite_query(query)
        p = [_serialize_param(x, to_sqlite=True) for x in params]
        async with aiosqlite.connect(_sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(q, p) as cursor:
                rows = await cursor.fetchall()
                return [_deserialize_row(dict(r)) for r in rows]

async def execute_returning_id(query: str, params: Union[tuple, list] = ()) -> Any:
    """Convenience helper to insert and get generated ID."""
    if is_postgres():
        if "RETURNING" not in query.upper():
            query = f"{query} RETURNING id"
        res = await fetch_one(query, params)
        return res["id"] if res else None
    else:
        q = _normalize_sqlite_query(query)
        # Remove RETURNING if present since SQLite cursor has lastrowid
        q_clean = re.sub(r"RETURNING\s+\w+", "", q, flags=re.IGNORECASE).strip()
        p = [_serialize_param(x, to_sqlite=True) for x in params]
        async with aiosqlite.connect(_sqlite_path) as db:
            cursor = await db.execute(q_clean, p)
            await db.commit()
            return cursor.lastrowid
