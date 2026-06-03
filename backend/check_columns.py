import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        r = await s.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='eval_results' AND column_name='langfuse_observation_id'"
        ))
        print('exists' if r.fetchone() else 'missing - needs migration')
    await engine.dispose()

asyncio.run(check())