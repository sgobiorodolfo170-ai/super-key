import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import inspect, text

from app.config import settings

logger = logging.getLogger(__name__)

_db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
if _db_path.startswith("./"):
    _db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), _db_path[2:])
os.makedirs(os.path.dirname(_db_path), exist_ok=True)

_resolved_url = f"sqlite+aiosqlite:///{_db_path}"

engine = create_async_engine(
    _resolved_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in _resolved_url else {}
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


_MIGRATIONS = {
    "providers": {
        "is_builtin": "BOOLEAN DEFAULT 1",
        "is_active": "BOOLEAN DEFAULT 1",
    },
    "model_classifications": {
        "is_builtin": "BOOLEAN DEFAULT 0",
        "is_active": "BOOLEAN DEFAULT 1",
    },
    "api_keys": {
        "is_active": "BOOLEAN DEFAULT 1",
    },
    "admin_users": {
        "is_active": "BOOLEAN DEFAULT 1",
    },
    "custom_models": {
        "is_active": "BOOLEAN DEFAULT 1",
    },
    "custom_model_channels": {
        "is_active": "BOOLEAN DEFAULT 1",
    },
    "channels": {
        "enable_auto_complete": "BOOLEAN DEFAULT 1",
        "auto_ban": "INTEGER DEFAULT 0",
        "model_mapping": "TEXT DEFAULT ''",
        "extra_headers": "TEXT DEFAULT ''",
        "extra_params": "TEXT DEFAULT ''",
        "param_override": "TEXT DEFAULT ''",
        "timeout": "INTEGER DEFAULT 60",
        "max_retries": "INTEGER DEFAULT 0",
        "test_model": "TEXT DEFAULT ''",
    },
    "request_logs": {
        "is_error": "BOOLEAN DEFAULT 0",
        "error_type": "TEXT DEFAULT ''",
        "error_message": "TEXT DEFAULT ''",
    },
}


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        if "sqlite" not in _resolved_url:
            return

        def _migrate(connection):
            insp = inspect(connection)
            migrated = 0
            for table_name, columns in _MIGRATIONS.items():
                if not insp.has_table(table_name):
                    continue
                existing = {col["name"] for col in insp.get_columns(table_name)}
                for col_name, col_def in columns.items():
                    if col_name not in existing:
                        connection.execute(
                            text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
                        )
                        migrated += 1
            if migrated:
                logger.info("Auto-migrated %d column(s) in existing tables", migrated)

        await conn.run_sync(_migrate)


async def get_session():
    async with async_session() as session:
        yield session
