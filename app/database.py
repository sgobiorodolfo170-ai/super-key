import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect, text, event

from app.config import settings

logger = logging.getLogger(__name__)

_db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
if _db_path.startswith("./"):
    _db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), _db_path[2:])
os.makedirs(os.path.dirname(_db_path), exist_ok=True)

_resolved_url = f"sqlite+aiosqlite:///{_db_path}"

_connect_args = {}
if "sqlite" in _resolved_url:
    _connect_args = {"check_same_thread": False}

engine = create_async_engine(
    _resolved_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    connect_args=_connect_args,
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _get_column_type_str(col):
    col_type = type(col.type).__name__
    if col_type == "Boolean":
        default_val = "1" if col.default and col.default.arg else "0"
        return f"BOOLEAN DEFAULT {default_val}"
    elif col_type == "Integer":
        default_val = col.default.arg if col.default and col.default.arg is not None else 0
        return f"INTEGER DEFAULT {default_val}"
    elif col_type == "Float":
        default_val = col.default.arg if col.default and col.default.arg is not None else 0.0
        return f"FLOAT DEFAULT {default_val}"
    elif col_type in ("String", "Text"):
        default_val = col.default.arg if col.default and col.default.arg is not None else ""
        escaped_val = str(default_val).replace("'", "''")
        return f"TEXT DEFAULT '{escaped_val}'"
    elif col_type == "DateTime":
        return "DATETIME"
    else:
        return f"TEXT DEFAULT ''"


async def init_db():
    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)

        if "sqlite" not in _resolved_url:
            return

        def _auto_migrate(connection):
            insp = inspect(connection)
            migrated = 0
            for table_name, table_obj in Base.metadata.tables.items():
                if not insp.has_table(table_name):
                    continue
                existing = {col["name"] for col in insp.get_columns(table_name)}
                for col_name, col_obj in table_obj.columns.items():
                    if col_name not in existing:
                        col_def = _get_column_type_str(col_obj)
                        try:
                            connection.execute(
                                text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
                            )
                            migrated += 1
                            logger.info("Auto-migrated: ALTER TABLE %s ADD COLUMN %s %s", table_name, col_name, col_def)
                        except Exception as e:
                            logger.warning("Migration failed for %s.%s: %s", table_name, col_name, e)
            if migrated:
                logger.info("Auto-migrated %d column(s) total", migrated)

        await conn.run_sync(_auto_migrate)


async def get_session():
    async with async_session() as session:
        yield session
