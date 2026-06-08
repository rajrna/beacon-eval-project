"""Check if pgvector is available in Postgres."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        try:
            await s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await s.commit()
            print("✅ pgvector is available and enabled")
        except Exception as e:
            print(f"❌ pgvector not available: {e}")
            print("\nFix: change your docker-compose.yml postgres image to:")
            print("  image: pgvector/pgvector:pg16")
            print("Then run: docker compose down && docker compose up postgres redis")
    await engine.dispose()

asyncio.run(check())