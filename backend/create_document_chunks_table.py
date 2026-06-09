"""
Create the document_chunks table for RAG document ingestion.
Run once before using the document upload feature.

Usage:
  python create_document_chunks_table.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text


async def migrate():
    engine = create_async_engine('postgresql+asyncpg://beacon:beacon@localhost:5435/beacon')
    async with async_sessionmaker(engine)() as s:

        # Documents table — one row per uploaded file
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS program_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
                filename VARCHAR(500) NOT NULL,
                original_filename VARCHAR(500) NOT NULL,
                file_size_bytes INTEGER,
                mime_type VARCHAR(100) DEFAULT 'application/pdf',
                category VARCHAR(50) DEFAULT 'general',
                description TEXT,
                chunk_count INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'processing',
                error_message TEXT,
                uploaded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await s.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_program_documents_program_id "
            "ON program_documents(program_id)"
        ))
        print("✓ Created program_documents table")

        # Document chunks table — one row per text chunk
        await s.execute(text("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL REFERENCES program_documents(id) ON DELETE CASCADE,
                program_id UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER,
                page_number INTEGER,
                embedding vector(1024),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
        await s.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id "
            "ON document_chunks(document_id)"
        ))
        await s.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_program_id "
            "ON document_chunks(program_id)"
        ))
        await s.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding
            ON document_chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 10)
        """))
        print("✓ Created document_chunks table with vector index")

        await s.commit()
    await engine.dispose()
    print("✅ Migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
