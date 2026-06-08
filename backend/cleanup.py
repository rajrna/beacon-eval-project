import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        await s.execute(text("DELETE FROM judges WHERE slug = 'hallucination_detection'"))
        await s.commit()
        print('Cleaned up partial judge')
    await engine.dispose()

asyncio.run(fix())