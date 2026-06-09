import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        r = await s.execute(text(
            "SELECT key, embedding IS NOT NULL as has_embedding, created_at "
            "FROM program_knowledge ORDER BY created_at DESC LIMIT 5"
        ))
        for row in r:
            print(f"key={row[0]:40s} embedded={row[1]} created={row[2]}")
    await engine.dispose()

asyncio.run(check())