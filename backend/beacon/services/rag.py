"""
RAG service — retrieval-augmented generation over program knowledge.

Embeds knowledge entries on save and retrieves relevant ones at query time.
Replaces the full knowledge block injection with targeted retrieval.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.knowledge import ProgramKnowledge

logger = structlog.get_logger(__name__)

# How many knowledge entries to retrieve per query
TOP_K = 5
# Minimum cosine similarity to include a result (0-1 scale)
SIMILARITY_THRESHOLD = 0.3


class RAGService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def embed_and_store(self, entry: ProgramKnowledge) -> None:
        """
        Generate embedding for a knowledge entry and store it.
        Called after creating or updating a knowledge entry.
        Best-effort — never raises.
        """
        try:
            from beacon.integrations.embeddings_client import embed_text

            # Build a rich text representation for embedding
            text_to_embed = _entry_to_text(entry)
            embedding = await embed_text(text_to_embed)

            # Store as pgvector — cast list to string format
            vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await self.session.execute(
                text(
                    "UPDATE program_knowledge SET embedding = :embedding::vector(1024) "
                    "WHERE id = :id"
                ),
                {"embedding": vector_str, "id": str(entry.id)},
            )
            await self.session.flush()
            logger.debug("knowledge_embedded", entry_id=str(entry.id), key=entry.key)
        except Exception as exc:
            logger.warning("knowledge_embed_failed", entry_id=str(entry.id), error=str(exc))

    async def embed_all(self, program_id: str) -> int:
        """
        Re-embed all knowledge entries for a program.
        Use this to backfill embeddings after migration or bulk import.
        Returns count of entries embedded.
        """
        from beacon.integrations.embeddings_client import embed_texts

        result = await self.session.execute(
            select(ProgramKnowledge).where(
                ProgramKnowledge.program_id == program_id,
                ProgramKnowledge.is_active == True,
            )
        )
        entries = result.scalars().all()
        if not entries:
            return 0

        texts = [_entry_to_text(e) for e in entries]
        embeddings = await embed_texts(texts)

        for entry, embedding in zip(entries, embeddings):
            vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await self.session.execute(
                text(
                    "UPDATE program_knowledge SET embedding = :embedding::vector(1024) "
                    "WHERE id = :id"
                ),
                {"embedding": vector_str, "id": str(entry.id)},
            )

        await self.session.flush()
        logger.info("knowledge_bulk_embedded", program_id=program_id, count=len(entries))
        return len(entries)

    async def retrieve(
        self,
        program_id: str,
        query: str,
        top_k: int = TOP_K,
    ) -> list[ProgramKnowledge]:
        """
        Retrieve the most relevant knowledge entries for a query.

        Embeds the query, does cosine similarity search against stored embeddings,
        returns top_k entries above the similarity threshold.

        Falls back to returning all entries if embeddings aren't available.
        """
        try:
            from beacon.integrations.embeddings_client import embed_text

            query_embedding = await embed_text(query)
            vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            # Check if any embeddings exist for this program
            count_result = await self.session.execute(
                text(
                    "SELECT COUNT(*) FROM program_knowledge "
                    "WHERE program_id = :pid AND embedding IS NOT NULL AND is_active = true"
                ),
                {"pid": program_id},
            )
            embedded_count = count_result.scalar()

            if embedded_count == 0:
                logger.warning("rag_no_embeddings_fallback", program_id=program_id)
                return await self._fallback_all(program_id)

            # Vector similarity search
            rows = await self.session.execute(
                text("""
                    SELECT id, 1 - (embedding <=> :query_vec::vector) as similarity
                    FROM program_knowledge
                    WHERE program_id = :pid
                      AND embedding IS NOT NULL
                      AND is_active = true
                      AND 1 - (embedding <=> :query_vec::vector(1024)) > :threshold
                    ORDER BY embedding <=> :query_vec::vector(1024)
                    LIMIT :top_k
                """),
                {
                    "query_vec": vector_str,
                    "pid": program_id,
                    "threshold": SIMILARITY_THRESHOLD,
                    "top_k": top_k,
                },
            )
            entry_ids = [str(row[0]) for row in rows.fetchall()]

            if not entry_ids:
                logger.debug("rag_no_results_fallback", program_id=program_id, query=query[:50])
                return await self._fallback_all(program_id)

            # Load full entries
            result = await self.session.execute(
                select(ProgramKnowledge).where(
                    ProgramKnowledge.id.in_(entry_ids)
                )
            )
            entries = result.scalars().all()
            logger.debug(
                "rag_retrieved",
                program_id=program_id,
                query=query[:50],
                count=len(entries),
            )
            return list(entries)

        except Exception as exc:
            logger.warning("rag_retrieve_failed", error=str(exc))
            return await self._fallback_all(program_id)

    async def _fallback_all(self, program_id: str) -> list[ProgramKnowledge]:
        """Return all active entries when vector search isn't available."""
        result = await self.session.execute(
            select(ProgramKnowledge).where(
                ProgramKnowledge.program_id == program_id,
                ProgramKnowledge.is_active == True,
            ).order_by(ProgramKnowledge.category, ProgramKnowledge.key)
        )
        return result.scalars().all()

    def build_context_block(self, entries: list[ProgramKnowledge]) -> str:
        """Format retrieved entries as a context block for the system prompt."""
        if not entries:
            return ""

        lines = ["--- RELEVANT PROGRAM FACTS ---"]
        for entry in entries:
            label = entry.display_label or entry.key.replace("_", " ").title()
            verified = f" (verified {entry.last_verified})" if entry.last_verified else ""
            lines.append(f"- {label}: {entry.value}{verified}")
        lines.append("--- END FACTS ---")
        return "\n".join(lines)


def _entry_to_text(entry: ProgramKnowledge) -> str:
    """
    Build a rich text representation of a knowledge entry for embedding.
    Including category, label, and value gives better semantic search results
    than embedding the value alone.
    """
    label = entry.display_label or entry.key.replace("_", " ")
    parts = [
        f"Category: {entry.category}",
        f"Topic: {label}",
        f"Information: {entry.value}",
    ]
    if entry.notes:
        parts.append(f"Notes: {entry.notes}")
    return " | ".join(parts)
