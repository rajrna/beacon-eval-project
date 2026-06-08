"""
Create the program_knowledge table.
Run once before starting the API with the knowledge feature.

Usage:
  python create_knowledge_table.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


async def migrate():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS program_knowledge (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
                category VARCHAR(50) NOT NULL,
                key VARCHAR(100) NOT NULL,
                value TEXT NOT NULL,
                display_label VARCHAR(255),
                effective_date DATE,
                expires_date DATE,
                source_url VARCHAR(500),
                last_verified DATE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                created_by_id UUID REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        # Indexes
        await s.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_program_knowledge_program_id ON program_knowledge(program_id)"
        ))
        await s.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_program_knowledge_category ON program_knowledge(program_id, category)"
        ))
        # Unique constraint — one value per key per program
        await s.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_program_knowledge_unique_key ON program_knowledge(program_id, key)"
        ))
        await s.commit()
        print("✓ Created program_knowledge table")
    await engine.dispose()
    print("✅ Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
