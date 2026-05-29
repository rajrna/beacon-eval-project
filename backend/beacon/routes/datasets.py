import uuid
from fastapi import APIRouter, Query
from beacon.auth.dependencies import CurrentUser, require_engineer_or_above, require_sme_or_above
from beacon.core.database import DbSession
from beacon.schemas.dataset import (
    DatasetCreate, DatasetResponse, DatasetUpdate,
    DatasetImportRequest, DatasetImportResponse,
    ExampleCreate, ExampleResponse, ExampleUpdate,
)
from beacon.schemas.base import PaginatedResponse
from beacon.services.dataset import DatasetService

router = APIRouter()

@router.get("", response_model=PaginatedResponse[DatasetResponse])
async def list_datasets(
    session: DbSession, current_user: CurrentUser,
    program_id: uuid.UUID = Query(...),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    return await DatasetService(session).list(program_id, limit=limit, offset=offset)

@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).get(dataset_id)

@router.post("", response_model=DatasetResponse, status_code=201, dependencies=[require_engineer_or_above()])
async def create_dataset(data: DatasetCreate, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).create(data)

@router.patch("/{dataset_id}", response_model=DatasetResponse, dependencies=[require_sme_or_above()])
async def update_dataset(dataset_id: uuid.UUID, data: DatasetUpdate, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).update(dataset_id, data)

@router.delete("/{dataset_id}", status_code=204, dependencies=[require_engineer_or_above()])
async def delete_dataset(dataset_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    await DatasetService(session).delete(dataset_id)

# ── Examples ──────────────────────────────────────────────────────────────────

@router.get("/{dataset_id}/examples", response_model=PaginatedResponse[ExampleResponse])
async def list_examples(
    dataset_id: uuid.UUID, session: DbSession, current_user: CurrentUser,
    limit: int = Query(default=50, le=200), offset: int = Query(default=0, ge=0),
    difficulty: str | None = None, persona: str | None = None,
):
    return await DatasetService(session).list_examples(dataset_id, limit=limit, offset=offset, difficulty=difficulty, persona=persona)

@router.get("/{dataset_id}/examples/{example_id}", response_model=ExampleResponse)
async def get_example(dataset_id: uuid.UUID, example_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).get_example(example_id)

@router.post("/{dataset_id}/examples", response_model=ExampleResponse, status_code=201, dependencies=[require_sme_or_above()])
async def create_example(dataset_id: uuid.UUID, data: ExampleCreate, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).create_example(dataset_id, data, created_by_id=current_user.id)

@router.patch("/{dataset_id}/examples/{example_id}", response_model=ExampleResponse, dependencies=[require_sme_or_above()])
async def update_example(dataset_id: uuid.UUID, example_id: uuid.UUID, data: ExampleUpdate, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).update_example(example_id, data)

@router.delete("/{dataset_id}/examples/{example_id}", status_code=204, dependencies=[require_sme_or_above()])
async def delete_example(dataset_id: uuid.UUID, example_id: uuid.UUID, session: DbSession, current_user: CurrentUser):
    await DatasetService(session).delete_example(example_id)

@router.post("/{dataset_id}/import", response_model=DatasetImportResponse, dependencies=[require_sme_or_above()])
async def import_examples(dataset_id: uuid.UUID, data: DatasetImportRequest, session: DbSession, current_user: CurrentUser):
    return await DatasetService(session).bulk_import(dataset_id, data, created_by_id=current_user.id)
