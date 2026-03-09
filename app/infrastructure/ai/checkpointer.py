from app.core.config import settings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager

# We use psycopg_pool for the PostgresSaver
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", "postgresql://"
).replace("postgresql+psycopg2://", "postgresql://")


@asynccontextmanager
async def get_checkpointer():
    """
    Provides a persistent Postgres-backed checkpointer for LangGraph.
    It uses a connection pool and yields the AsyncPostgresSaver.
    """
    async with AsyncConnectionPool(
        conninfo=DATABASE_URL,
        max_size=20,
        kwargs={
            "autocommit": None,  # AsyncConnectionPool defaults handles autocommit differently or None
            "prepare_threshold": 0,
        },
    ) as pool:
        saver = AsyncPostgresSaver(pool)
        # Ensure the schema is configured
        await saver.setup()
        yield saver
