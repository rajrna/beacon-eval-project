"""
Add embedding column to program_knowledge table.
Run once after enabling pgvector.

Usage:
  python rag_migration.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


async def migrate():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:
        # Ensure pgvector extension is enabled
        await s.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Add embedding column (1536 dims for Titan Embed v2, 1024 for v1)
        try:
            await s.execute(text(
                "ALTER TABLE program_knowledge ADD COLUMN embedding vector(1024)"
            ))
            print("✓ Added embedding column (1536 dims)")
        except Exception as e:
            if "already exists" in str(e):
                print("· embedding column already exists")
            else:
                raise

        # Add IVFFlat index for fast approximate nearest-neighbour search
        try:
            await s.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_program_knowledge_embedding
                ON program_knowledge
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 10)
            """))
            print("✓ Created IVFFlat index on embedding column")
        except Exception as e:
            print(f"· Index creation note: {e}")

        await s.commit()
    await engine.dispose()
    print("\n✅ RAG migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
