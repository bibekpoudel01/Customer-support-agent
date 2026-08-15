import os
import logfire


_pool = None
_async_pool = None

async def get_async_db_pool():
    """
    Returns an asynchronous psycopg3 connection pool.
    Used by LangGraph AsyncPostgresSaver.
    """
    global _async_pool

    if _async_pool is not None:
        return _async_pool

    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")

    if not all([db_host, db_user, db_pass, db_name]):
        logfire.info("ℹ️ DB env vars not set — async Postgres pool skipped")
        return None

    try:
        from psycopg_pool import AsyncConnectionPool

        conninfo = (
            f"host={db_host} "
            f"dbname={db_name} "
            f"user={db_user} "
            f"password={db_pass}"
        )

        _async_pool = AsyncConnectionPool(
            conninfo,
            min_size=1,
            max_size=5,
            open=False,
            kwargs={"autocommit": True},
        )

        await _async_pool.open()

        logfire.info("✅ Async Postgres connection pool initialized")

        return _async_pool

    except Exception as e:
        logfire.error(f"❌ Async Postgres pool init failed: {e}")
        return None


async def close_async_db_pool():
    global _async_pool

    if _async_pool is not None:
        await _async_pool.close()
        _async_pool = None

        logfire.info("✅ Async Postgres connection pool closed")