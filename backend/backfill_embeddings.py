"""
Backfill embeddings for all existing program knowledge entries.
Run once after deploying RAG migration.

Usage:
  python backfill_embeddings.py
  python backfill_embeddings.py --program-id <uuid>  # specific program only
"""
import asyncio
import sys


async def backfill(program_id: str | None = None) -> None:
    from beacon.core.settings import get_settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text
    from beacon.services.rag import RAGService

    settings = get_settings()
    engine = create_async_engine(settings.database_url_str)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        if program_id:
            program_ids = [program_id]
        else:
            result = await session.execute(text("SELECT id, name FROM programs"))
            rows = result.fetchall()
            program_ids = [str(r[0]) for r in rows]
            print(f"Found {len(program_ids)} programs")

        rag = RAGService(session)
        total = 0

        for pid in program_ids:
            # Get program name
            name_result = await session.execute(
                text(f"SELECT name FROM programs WHERE id = '{pid}'")
            )
            name_row = name_result.fetchone()
            name = name_row[0] if name_row else pid[:8]

            print(f"\nEmbedding knowledge for: {name}")
            count = await rag.embed_all(pid)
            await session.commit()
            print(f"  ✓ {count} entries embedded")
            total += count

    await engine.dispose()
    print(f"\n✅ Done — {total} knowledge entries embedded total.")


if __name__ == "__main__":
    program_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--program-id":
        program_id = sys.argv[2]
    asyncio.run(backfill(program_id))
