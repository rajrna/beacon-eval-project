"""
RAG service — retrieval-augmented generation over program knowledge.

Features:
- Query rewriting: converts conversational messages to clean search queries
- Hybrid search: vector similarity + keyword fallback
- Knowledge gap detection: logs queries that return no results
"""
from __future__ import annotations

import logging

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.knowledge import ProgramKnowledge

logger = structlog.get_logger(__name__)

TOP_K = 5
SIMILARITY_THRESHOLD = 0.3


class RAGService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def embed_and_store(self, entry: ProgramKnowledge) -> None:
        """Embed a knowledge entry and store it. Best-effort."""
        try:
            from beacon.integrations.embeddings_client import embed_text
            text_to_embed = _entry_to_text(entry)
            embedding = await embed_text(text_to_embed)
            vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await self.session.execute(
                text("UPDATE program_knowledge SET embedding = CAST(:embedding AS vector(1024)) WHERE id = :id"),
                {"embedding": vector_str, "id": str(entry.id)},
            )
            await self.session.flush()
            logger.debug("knowledge_embedded", entry_id=str(entry.id), key=entry.key)
        except Exception as exc:
            logger.warning("knowledge_embed_failed", entry_id=str(entry.id), error=str(exc))

    async def embed_all(self, program_id: str) -> int:
        """Re-embed all knowledge entries for a program. Returns count embedded."""
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
                text("UPDATE program_knowledge SET embedding = CAST(:embedding AS vector(1024)) WHERE id = :id"),
                {"embedding": vector_str, "id": str(entry.id)},
            )
        await self.session.flush()
        logger.info("knowledge_bulk_embedded", program_id=program_id, count=len(entries))
        return len(entries)

    async def _rewrite_query(self, query: str) -> str:
        """
        Rewrite a conversational student query into a clean search query.
        Falls back to original query if rewriting fails.
        """
        try:
            from beacon.integrations.anthropic_client import complete_structured

            prompt = f"""You are a search query optimizer for a medical school knowledge base.

Convert this student message into a short, precise search query (5-8 words max).
Focus on key topics: admissions, tuition, financial aid, requirements, deadlines, policies, clinical training, career.
Remove emotional language, filler words, and personal details.
Return ONLY the search query — no explanation, no punctuation, no quotes.

Student message: {query}

Search query:"""

            rewritten = await complete_structured(
                prompt=prompt,
                system="You are a search query optimizer. Return only the search query, nothing else.",
                max_tokens=50,
                temperature=0.0,
            )
            rewritten = rewritten.strip().strip('"').strip("'")
            if rewritten and len(rewritten) > 3:
                logger.debug("rag_query_rewritten", original=query[:80], rewritten=rewritten)
                return rewritten
            return query
        except Exception as exc:
            logger.debug("rag_query_rewrite_failed", error=str(exc))
            return query

    async def retrieve(
        self,
        program_id: str,
        query: str,
        top_k: int = TOP_K,
        rewrite_query: bool = True,
    ) -> tuple[list[ProgramKnowledge], str]:
        """
        Hybrid retrieval: query rewriting + vector similarity + keyword fallback.

        Returns a tuple of (entries, rewritten_query) so callers can log
        the rewritten query for observability.
        """
        try:
            from beacon.integrations.embeddings_client import embed_text

            # ── Query rewriting ───────────────────────────────────────────────
            search_query = query
            if rewrite_query:
                search_query = await self._rewrite_query(query)

            # Check if embeddings exist
            count_result = await self.session.execute(
                text(
                    "SELECT COUNT(*) FROM program_knowledge "
                    "WHERE program_id = :pid AND embedding IS NOT NULL AND is_active = true"
                ),
                {"pid": program_id},
            )
            embedded_count = count_result.scalar()

            vector_ids: list[str] = []
            keyword_ids: list[str] = []

            # ── Vector search using rewritten query ───────────────────────────
            if embedded_count > 0:
                query_embedding = await embed_text(search_query)
                vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
                rows = await self.session.execute(
                    text("""
                        SELECT id, 1 - (embedding <=> :query_vec::vector(1024)) as similarity
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
                vector_ids = [str(row[0]) for row in rows.fetchall()]
                logger.debug(
                    "rag_vector_results",
                    program_id=program_id,
                    original_query=query[:50],
                    search_query=search_query[:50],
                    count=len(vector_ids),
                )

            # ── Keyword search using BOTH original and rewritten query ─────────
            keywords = list(set(
                _extract_keywords(query) + _extract_keywords(search_query)
            ))[:6]

            if keywords:
                keyword_conditions = " OR ".join([
                    f"(value ILIKE :kw{i} OR display_label ILIKE :kw{i} OR key ILIKE :kw{i})"
                    for i in range(len(keywords))
                ])
                kw_params = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(keywords)}
                kw_params["pid"] = program_id
                kw_params["top_k"] = top_k
                kw_rows = await self.session.execute(
                    text(f"""
                        SELECT id FROM program_knowledge
                        WHERE program_id = :pid
                          AND is_active = true
                          AND ({keyword_conditions})
                        LIMIT :top_k
                    """),
                    kw_params,
                )
                keyword_ids = [str(row[0]) for row in kw_rows.fetchall()]
                logger.debug(
                    "rag_keyword_results",
                    program_id=program_id,
                    keywords=keywords,
                    count=len(keyword_ids),
                )

            # ── Merge (vector first, keyword fills gaps) ──────────────────────
            merged_ids: dict[str, None] = {}
            for eid in vector_ids:
                merged_ids[eid] = None
            for eid in keyword_ids:
                if len(merged_ids) >= top_k:
                    break
                merged_ids[eid] = None

            all_ids = list(merged_ids.keys())

            if not all_ids:
                await self._log_knowledge_gap(program_id, query)
                logger.info("rag_knowledge_gap", program_id=program_id, query=query[:100])
                return await self._fallback_all(program_id), search_query

            result = await self.session.execute(
                select(ProgramKnowledge).where(ProgramKnowledge.id.in_(all_ids))
            )
            entries = result.scalars().all()
            logger.debug(
                "rag_hybrid_retrieved",
                program_id=program_id,
                original_query=query[:50],
                search_query=search_query[:50],
                vector_count=len(vector_ids),
                keyword_count=len(keyword_ids),
                total=len(entries),
            )
            return list(entries), search_query

        except Exception as exc:
            logger.warning("rag_retrieve_failed", error=str(exc))
            return await self._fallback_all(program_id), query

    async def _log_knowledge_gap(self, program_id: str, query: str) -> None:
        """Log a query that returned no results. Best-effort."""
        try:
            await self.session.execute(text("""
                INSERT INTO knowledge_gaps (
                    id, program_id, query, occurred_at, occurrence_count
                )
                VALUES (gen_random_uuid(), :program_id, :query, NOW(), 1)
                ON CONFLICT (program_id, query)
                DO UPDATE SET
                    occurrence_count = knowledge_gaps.occurrence_count + 1,
                    last_occurred_at = NOW()
            """), {"program_id": program_id, "query": query[:500]})
            await self.session.flush()
        except Exception as exc:
            logger.warning("knowledge_gap_log_failed", error=str(exc))

    async def get_knowledge_gaps(self, program_id: str, limit: int = 20) -> list[dict]:
        """Return the most common unanswered queries for a program."""
        try:
            rows = await self.session.execute(text("""
                SELECT query, occurrence_count, occurred_at, last_occurred_at
                FROM knowledge_gaps
                WHERE program_id = :pid
                ORDER BY occurrence_count DESC, last_occurred_at DESC
                LIMIT :limit
            """), {"pid": program_id, "limit": limit})
            return [
                {
                    "query": row[0],
                    "occurrence_count": row[1],
                    "first_seen": row[2].isoformat() if row[2] else None,
                    "last_seen": row[3].isoformat() if row[3] else None,
                }
                for row in rows.fetchall()
            ]
        except Exception as exc:
            logger.warning("knowledge_gaps_fetch_failed", error=str(exc))
            return []

    async def _fallback_all(self, program_id: str) -> list[ProgramKnowledge]:
        """Return all active entries when retrieval finds nothing."""
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
    """Build rich text for embedding."""
    label = entry.display_label or entry.key.replace("_", " ")
    parts = [
        f"Category: {entry.category}",
        f"Topic: {label}",
        f"Information: {entry.value}",
    ]
    if entry.notes:
        parts.append(f"Notes: {entry.notes}")
    return " | ".join(parts)


def _extract_keywords(query: str) -> list[str]:
    """Extract meaningful keywords, filtering stop words."""
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "i", "me", "my",
        "we", "our", "you", "your", "what", "how", "when", "where",
        "why", "who", "which", "that", "this", "these", "those",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "about", "tell", "know", "want", "need", "please", "help",
    }
    words = query.lower().split()
    keywords = [
        w.strip("?.,!") for w in words
        if len(w) > 3 and w.strip("?.,!") not in stop_words
    ]
    return keywords[:5]