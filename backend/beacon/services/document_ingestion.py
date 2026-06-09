"""
Document ingestion pipeline for Beacon.

Handles PDF parsing, text chunking, and embedding for RAG.
Stores chunks in document_chunks table with pgvector embeddings.

Pipeline:
  1. Parse PDF → extract text per page
  2. Split into overlapping chunks (~500 tokens each)
  3. Embed each chunk via Bedrock Titan Embed v2
  4. Store in document_chunks table
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Chunk size in characters (approx 500 tokens at 4 chars/token)
CHUNK_SIZE = 2000
# Overlap between chunks to preserve context across boundaries
CHUNK_OVERLAP = 200
# Minimum chunk size — discard chunks smaller than this
MIN_CHUNK_SIZE = 100


class DocumentIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest_pdf(
        self,
        program_id: str,
        filename: str,
        original_filename: str,
        file_bytes: bytes,
        category: str = "general",
        description: str | None = None,
        uploaded_by_id: str | None = None,
    ) -> dict:
        """
        Full ingestion pipeline for a PDF file.

        1. Create document record
        2. Extract text from PDF
        3. Split into chunks
        4. Embed all chunks
        5. Store chunks in DB
        6. Update document status

        Returns document metadata dict.
        """
        # Create document record
        doc_id = str(uuid.uuid4())
        await self.session.execute(text("""
            INSERT INTO program_documents (
                id, program_id, filename, original_filename,
                file_size_bytes, category, description,
                status, uploaded_by_id, created_at, updated_at
            ) VALUES (
                :id, :program_id, :filename, :original_filename,
                :file_size_bytes, :category, :description,
                'processing', :uploaded_by_id, NOW(), NOW()
            )
        """), {
            "id": doc_id,
            "program_id": program_id,
            "filename": filename,
            "original_filename": original_filename,
            "file_size_bytes": len(file_bytes),
            "category": category,
            "description": description,
            "uploaded_by_id": uploaded_by_id,
        })
        await self.session.flush()

        try:
            # Extract text from PDF
            pages = _extract_pdf_text(file_bytes)
            full_text = "\n\n".join(
                f"[Page {i+1}]\n{page}" for i, page in enumerate(pages) if page.strip()
            )

            if not full_text.strip():
                raise ValueError("No text could be extracted from the PDF. It may be scanned or image-based.")

            # Chunk the text
            chunks = _chunk_text(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
            logger.info(
                "document_chunked",
                doc_id=doc_id,
                filename=original_filename,
                pages=len(pages),
                chunks=len(chunks),
            )

            # Embed all chunks
            from beacon.integrations.embeddings_client import embed_texts
            embeddings = await embed_texts([c["content"] for c in chunks])

            # Store chunks
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
                await self.session.execute(text("""
                    INSERT INTO document_chunks (
                        id, document_id, program_id, chunk_index,
                        content, token_count, page_number, embedding, created_at
                    ) VALUES (
                        gen_random_uuid(), :doc_id, :program_id, :chunk_index,
                        :content, :token_count, :page_number,
                        CAST(:embedding AS vector(1024)), NOW()
                    )
                """), {
                    "doc_id": doc_id,
                    "program_id": program_id,
                    "chunk_index": i,
                    "content": chunk["content"],
                    "token_count": len(chunk["content"]) // 4,
                    "page_number": chunk.get("page_number"),
                    "embedding": vector_str,
                })

            # Update document status
            await self.session.execute(text("""
                UPDATE program_documents
                SET status = 'ready',
                    chunk_count = :chunk_count,
                    updated_at = NOW()
                WHERE id = :id
            """), {"id": doc_id, "chunk_count": len(chunks)})

            await self.session.flush()

            logger.info(
                "document_ingested",
                doc_id=doc_id,
                filename=original_filename,
                chunks=len(chunks),
            )

            return {
                "id": doc_id,
                "filename": original_filename,
                "status": "ready",
                "pages": len(pages),
                "chunks": len(chunks),
            }

        except Exception as exc:
            # Mark document as failed
            await self.session.execute(text("""
                UPDATE program_documents
                SET status = 'failed',
                    error_message = :error,
                    updated_at = NOW()
                WHERE id = :id
            """), {"id": doc_id, "error_message": str(exc)[:500]})
            await self.session.flush()
            logger.error("document_ingestion_failed", doc_id=doc_id, error=str(exc))
            raise

    async def list_documents(self, program_id: str) -> list[dict]:
        """List all documents for a program."""
        rows = await self.session.execute(text("""
            SELECT id, original_filename, category, description,
                   file_size_bytes, chunk_count, status, error_message, created_at
            FROM program_documents
            WHERE program_id = :pid
            ORDER BY created_at DESC
        """), {"pid": program_id})

        return [
            {
                "id": str(row[0]),
                "filename": row[1],
                "category": row[2],
                "description": row[3],
                "file_size_bytes": row[4],
                "chunk_count": row[5],
                "status": row[6],
                "error_message": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
            }
            for row in rows.fetchall()
        ]

    async def delete_document(self, document_id: str) -> None:
        """Delete a document and all its chunks."""
        await self.session.execute(
            text("DELETE FROM program_documents WHERE id = :id"),
            {"id": document_id}
        )
        await self.session.flush()

    async def retrieve_chunks(
        self,
        program_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Retrieve the most relevant document chunks for a query.
        Used by RAGService to augment knowledge entry retrieval.
        """
        try:
            from beacon.integrations.embeddings_client import embed_text
            query_embedding = await embed_text(query)
            vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            rows = await self.session.execute(text("""
                SELECT
                    dc.content,
                    dc.page_number,
                    pd.original_filename,
                    pd.category,
                    1 - (dc.embedding <=> CAST(:query_vec AS vector(1024))) as similarity
                FROM document_chunks dc
                JOIN program_documents pd ON dc.document_id = pd.id
                WHERE dc.program_id = :pid
                  AND pd.status = 'ready'
                  AND 1 - (dc.embedding <=> CAST(:query_vec AS vector(1024))) > 0.3
                ORDER BY dc.embedding <=> CAST(:query_vec AS vector(1024))
                LIMIT :top_k
            """), {
                "query_vec": vector_str,
                "pid": program_id,
                "top_k": top_k,
            })

            return [
                {
                    "content": row[0],
                    "page_number": row[1],
                    "filename": row[2],
                    "category": row[3],
                    "similarity": float(row[4]),
                }
                for row in rows.fetchall()
            ]

        except Exception as exc:
            logger.warning("document_chunk_retrieve_failed", error=str(exc))
            return []


# ── PDF parsing ───────────────────────────────────────────────────────────────

def _extract_pdf_text(file_bytes: bytes) -> list[str]:
    """
    Extract text from PDF bytes. Returns list of page texts.
    Uses pypdf (install with: pip install pypdf)
    """
    try:
        import pypdf
        import io
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            # Clean up common PDF extraction artifacts
            text = re.sub(r'\s+', ' ', text).strip()
            pages.append(text)
        return pages
    except ImportError:
        raise ImportError(
            "pypdf is required for PDF parsing. "
            "Install with: pip install pypdf"
        )
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF: {exc}")


# ── Text chunking ─────────────────────────────────────────────────────────────

def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.

    Tries to split on paragraph boundaries first, then sentence
    boundaries, falling back to character-level splitting.
    Preserves page number markers from the text.
    """
    chunks = []
    current_page = 1

    # Split on paragraph boundaries
    paragraphs = re.split(r'\n\n+', text)

    current_chunk = ""
    current_page = 1

    for para in paragraphs:
        # Track page numbers
        page_match = re.match(r'\[Page (\d+)\]', para.strip())
        if page_match:
            current_page = int(page_match.group(1))
            para = re.sub(r'\[Page \d+\]\s*', '', para).strip()

        if not para.strip():
            continue

        # If adding this paragraph exceeds chunk size, save current chunk
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            if len(current_chunk) >= MIN_CHUNK_SIZE:
                chunks.append({
                    "content": current_chunk.strip(),
                    "page_number": current_page,
                })
            # Start new chunk with overlap
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    # Add final chunk
    if current_chunk.strip() and len(current_chunk) >= MIN_CHUNK_SIZE:
        chunks.append({
            "content": current_chunk.strip(),
            "page_number": current_page,
        })

    return chunks
