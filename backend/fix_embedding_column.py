import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def fix():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        await s.execute(text("ALTER TABLE program_knowledge DROP COLUMN IF EXISTS embedding"))
        await s.execute(text("ALTER TABLE program_knowledge ADD COLUMN embedding vector(1024)"))
        await s.commit()
        print("Done")
    await engine.dispose()

asyncio.run(fix())