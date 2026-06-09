"""
Program Knowledge routes.
Scoped under /v1/programs/{program_id}/knowledge
"""
import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above
from beacon.core.database import DbSession
from beacon.schemas.knowledge import (
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeEntryResponse,
    KnowledgeBulkCreate,
)
from beacon.schemas.base import PaginatedResponse
from beacon.services.knowledge import KnowledgeService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[KnowledgeEntryResponse])
async def list_knowledge(
    program_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    category: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    return await KnowledgeService(session).list(
        program_id, category=category, active_only=active_only,
        limit=limit, offset=offset,
    )


@router.post("", response_model=KnowledgeEntryResponse, status_code=201)
async def create_knowledge_entry(
    program_id: uuid.UUID,
    data: KnowledgeEntryCreate,
    session: DbSession,
    current_user: CurrentUser,
):
    return await KnowledgeService(session).create(
        program_id, data, created_by_id=current_user.id
    )


@router.post("/bulk", response_model=list[KnowledgeEntryResponse], status_code=201)
async def bulk_create_knowledge(
    program_id: uuid.UUID,
    data: KnowledgeBulkCreate,
    session: DbSession,
    current_user: CurrentUser,
):
    """Upload multiple knowledge entries at once. Upserts by key."""
    return await KnowledgeService(session).bulk_create(
        program_id, data.entries, created_by_id=current_user.id
    )


@router.get("/prompt-block", response_model=dict)
async def get_knowledge_prompt_block(
    program_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
):
    """Preview the knowledge block that gets injected into agent prompts."""
    block = await KnowledgeService(session).build_knowledge_block(program_id)
    return {"block": block, "empty": not bool(block)}


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge_entry(
    program_id: uuid.UUID,
    entry_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
):
    return await KnowledgeService(session).get(entry_id)


@router.patch("/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_knowledge_entry(
    program_id: uuid.UUID,
    entry_id: uuid.UUID,
    data: KnowledgeEntryUpdate,
    session: DbSession,
    current_user: CurrentUser,
):
    return await KnowledgeService(session).update(entry_id, data)


@router.delete("/{entry_id}", status_code=204)
async def delete_knowledge_entry(
    program_id: uuid.UUID,
    entry_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
):
    await KnowledgeService(session).delete(entry_id)

@router.get("/gaps", response_model=list[dict])
async def get_knowledge_gaps(
    program_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, le=100),
):
    """
    Return the most common queries that returned no RAG results.
    Use this to identify what knowledge entries to add next.
    Sorted by frequency — most common gaps first.
    """
    from beacon.services.rag import RAGService
    rag = RAGService(session)
    return await rag.get_knowledge_gaps(str(program_id), limit=limit)
 