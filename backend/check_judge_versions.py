import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        r = await s.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'judge_versions' ORDER BY ordinal_position"
        ))
        for row in r:
            print(row)
    await engine.dispose()

asyncio.run(check())