"""
ProgramKnowledge service.

Handles CRUD for program knowledge entries and builds
the knowledge block injected into agent system prompts.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

import structlog
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.knowledge import ProgramKnowledge
from beacon.schemas.knowledge import (
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeEntryResponse,
)
from beacon.schemas.base import PaginatedResponse

logger = structlog.get_logger(__name__)

# Category display order for prompt injection
CATEGORY_ORDER = [
    "admissions",
    "requirements",
    "deadlines",
    "tuition",
    "financial_aid",
    "policies",
    "clinical",
    "career",
    "general",
]

CATEGORY_LABELS = {
    "admissions": "Admissions",
    "requirements": "Prerequisites & Requirements",
    "deadlines": "Important Deadlines",
    "tuition": "Tuition & Fees",
    "financial_aid": "Financial Aid",
    "policies": "Policies",
    "clinical": "Clinical Education",
    "career": "Career & Residency",
    "general": "General Information",
}


class KnowledgeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        program_id: uuid.UUID,
        category: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> PaginatedResponse[KnowledgeEntryResponse]:
        q = select(ProgramKnowledge).where(
            ProgramKnowledge.program_id == program_id
        )
        if category:
            q = q.where(ProgramKnowledge.category == category)
        if active_only:
            q = q.where(ProgramKnowledge.is_active == True)
        q = q.order_by(ProgramKnowledge.category, ProgramKnowledge.key)

        count_q = q
        total_result = await self.session.execute(count_q)
        total = len(total_result.scalars().all())

        result = await self.session.execute(q.offset(offset).limit(limit))
        items = [KnowledgeEntryResponse.model_validate(r) for r in result.scalars().all()]

        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get(self, entry_id: uuid.UUID) -> KnowledgeEntryResponse:
        result = await self.session.execute(
            select(ProgramKnowledge).where(ProgramKnowledge.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found")
        return KnowledgeEntryResponse.model_validate(entry)

    async def create(
        self,
        program_id: uuid.UUID,
        data: KnowledgeEntryCreate,
        created_by_id: uuid.UUID | None = None,
    ) -> KnowledgeEntryResponse:
        entry = ProgramKnowledge(
            program_id=program_id,
            created_by_id=created_by_id,
            **data.model_dump(),
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)

        try:
            from beacon.services.rag import RAGService
            await RAGService(self.session).embed_and_store(entry)
        except Exception as exc:
            logger.warning("knowledge_auto_embed_fialed", key=data.key, error=str(exc))    

        logger.info("knowledge_entry_created", program_id=str(program_id), key=data.key, category=data.category)
        return KnowledgeEntryResponse.model_validate(entry)

    async def bulk_create(
        self,
        program_id: uuid.UUID,
        entries: list[KnowledgeEntryCreate],
        created_by_id: uuid.UUID | None = None,
    ) -> list[KnowledgeEntryResponse]:
        created = []
        for data in entries:
            # Upsert by key — update if exists, create if not
            existing = await self.session.execute(
                select(ProgramKnowledge).where(
                    ProgramKnowledge.program_id == program_id,
                    ProgramKnowledge.key == data.key,
                )
            )
            entry = existing.scalar_one_or_none()
            if entry:
                for field, value in data.model_dump(exclude_none=True).items():
                    setattr(entry, field, value)
            else:
                entry = ProgramKnowledge(
                    program_id=program_id,
                    created_by_id=created_by_id,
                    **data.model_dump(),
                )
                self.session.add(entry)
            await self.session.flush()
            await self.session.refresh(entry)

            try:
                from beacon.services.rag import RAGService
                await RAGService(self.session).embed_and_store(entry)
            except Exception as exc:
                logger.warning("knowledge_auto_embed_failed", key=data.key, error=str(exc))

            created.append(KnowledgeEntryResponse.model_validate(entry))

        await self.session.commit()
        logger.info("knowledge_bulk_created", program_id=str(program_id), count=len(created))
        return created

    async def update(
        self,
        entry_id: uuid.UUID,
        data: KnowledgeEntryUpdate,
    ) -> KnowledgeEntryResponse:
        result = await self.session.execute(
            select(ProgramKnowledge).where(ProgramKnowledge.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(entry, field, value)
        await self.session.flush()
        await self.session.refresh(entry)
        try:
            from beacon.services.rag import RAGService
            await RAGService(self.session).embed_and_store(entry)
        except Exception as exc:
            logger.warning("knowledge_auto_embed_failed", entry_id=str(entry_id), error=str(exc))
        
        return KnowledgeEntryResponse.model_validate(entry)

    async def delete(self, entry_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(ProgramKnowledge).where(ProgramKnowledge.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found")
        await self.session.delete(entry)
        await self.session.flush()

    async def build_knowledge_block(self, program_id: uuid.UUID) -> str:
        """
        Build a formatted knowledge block for injection into agent system prompts.

        Returns a string like:
        --- PROGRAM KNOWLEDGE BASE ---
        ADMISSIONS
        - Average MCAT: 522.2
        - Average GPA: 3.9
        ...
        """
        result = await self.session.execute(
            select(ProgramKnowledge).where(
                ProgramKnowledge.program_id == program_id,
                ProgramKnowledge.is_active == True,
            ).order_by(ProgramKnowledge.category, ProgramKnowledge.key)
        )
        entries = result.scalars().all()

        if not entries:
            return ""

        # Group by category
        by_category: dict[str, list[ProgramKnowledge]] = {}
        for entry in entries:
            if entry.category not in by_category:
                by_category[entry.category] = []
            by_category[entry.category].append(entry)

        lines = ["--- PROGRAM KNOWLEDGE BASE ---"]
        lines.append("Use the following verified facts when answering student questions.")
        lines.append("Always cite these figures rather than estimating or approximating.\n")

        for category in CATEGORY_ORDER:
            if category not in by_category:
                continue
            label = CATEGORY_LABELS.get(category, category.title())
            lines.append(f"{label.upper()}")
            for entry in by_category[category]:
                display = entry.display_label or entry.key.replace("_", " ").title()
                # Add verification date if available
                verified = f" (verified {entry.last_verified})" if entry.last_verified else ""
                lines.append(f"- {display}: {entry.value}{verified}")
            lines.append("")

        lines.append("--- END KNOWLEDGE BASE ---")
        return "\n".join(lines)
