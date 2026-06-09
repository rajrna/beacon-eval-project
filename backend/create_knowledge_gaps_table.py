"""
Create the knowledge_gaps table for tracking unanswered RAG queries.
Run once before deploying the updated RAG service.

Usage:
  python create_knowledge_gaps_table.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


async def migrate():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
                query TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_occurred_at TIMESTAMPTZ,
                occurrence_count INTEGER NOT NULL DEFAULT 1
            )
        """))

        # Unique constraint so ON CONFLICT works
        await s.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_knowledge_gaps_program_query
            ON knowledge_gaps(program_id, query)
        """))

        # Index for fast lookup by program + frequency
        await s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_knowledge_gaps_program_count
            ON knowledge_gaps(program_id, occurrence_count DESC)
        """))

        await s.commit()
        print("✓ Created knowledge_gaps table")
    await engine.dispose()
    print("✅ Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
