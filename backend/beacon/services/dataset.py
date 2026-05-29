import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.dataset import Dataset, Example
from beacon.repositories.dataset import DatasetRepository, ExampleRepository
from beacon.schemas.base import PaginatedResponse
from beacon.schemas.dataset import (
    DatasetCreate, DatasetImportRequest, DatasetImportResponse,
    DatasetResponse, DatasetUpdate,
    ExampleCreate, ExampleResponse, ExampleUpdate,
)


class DatasetService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = DatasetRepository(session)
        self.example_repo = ExampleRepository(session)

    async def list(
        self, program_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[DatasetResponse]:
        rows, total = await self.repo.list_by_program(program_id, limit=limit, offset=offset)
        items = []
        for ds in rows:
            count = await self.repo.get_example_count(ds.id)
            items.append(self._to_response(ds, count))
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get(self, dataset_id: uuid.UUID) -> DatasetResponse:
        ds = await self.repo.get_by_id(dataset_id)
        if not ds:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        count = await self.repo.get_example_count(dataset_id)
        return self._to_response(ds, count)

    async def create(self, data: DatasetCreate) -> DatasetResponse:
        ds = Dataset(**data.model_dump())
        ds = await self.repo.create(ds)
        return self._to_response(ds, 0)

    async def update(self, dataset_id: uuid.UUID, data: DatasetUpdate) -> DatasetResponse:
        ds = await self.repo.get_by_id(dataset_id)
        if not ds:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(ds, field, value)
        await self.repo.flush()
        return await self.get(dataset_id)

    async def delete(self, dataset_id: uuid.UUID) -> None:
        ds = await self.repo.get_by_id(dataset_id)
        if not ds:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        await self.repo.delete(ds)

    # ── Examples ──────────────────────────────────────────────────────────────

    async def list_examples(
        self,
        dataset_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        difficulty: str | None = None,
        persona: str | None = None,
    ) -> PaginatedResponse[ExampleResponse]:
        rows, total = await self.example_repo.list_by_dataset(
            dataset_id, limit=limit, offset=offset, difficulty=difficulty, persona=persona
        )
        items = [self._example_to_response(e) for e in rows]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get_example(self, example_id: uuid.UUID) -> ExampleResponse:
        ex = await self.example_repo.get_by_id(example_id)
        if not ex:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")
        return self._example_to_response(ex)

    async def create_example(
        self, dataset_id: uuid.UUID, data: ExampleCreate, created_by_id: uuid.UUID | None = None
    ) -> ExampleResponse:
        ds = await self.repo.get_by_id(dataset_id)
        if not ds:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
        ex = Example(
            dataset_id=dataset_id,
            created_by_id=created_by_id,
            is_safety_tagged=bool(data.safety_tags),
            **data.model_dump(),
        )
        ex = await self.example_repo.create(ex)
        await self.repo.bump_version(ds)
        return self._example_to_response(ex)

    async def update_example(
        self, example_id: uuid.UUID, data: ExampleUpdate
    ) -> ExampleResponse:
        ex = await self.example_repo.get_by_id(example_id)
        if not ex:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(ex, field, value)
        if ex.safety_tags:
            ex.is_safety_tagged = True
        await self.example_repo.flush()
        return self._example_to_response(ex)

    async def delete_example(self, example_id: uuid.UUID) -> None:
        ex = await self.example_repo.get_by_id(example_id)
        if not ex:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Example not found")
        ds = await self.repo.get_by_id(ex.dataset_id)
        await self.example_repo.delete(ex)
        if ds:
            await self.repo.bump_version(ds)

    async def bulk_import(
        self, dataset_id: uuid.UUID, data: DatasetImportRequest, created_by_id: uuid.UUID | None = None
    ) -> DatasetImportResponse:
        ds = await self.repo.get_by_id(dataset_id)
        if not ds:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

        examples = []
        errors = []
        for i, ex_data in enumerate(data.examples):
            try:
                ex = Example(
                    dataset_id=dataset_id,
                    created_by_id=created_by_id,
                    is_safety_tagged=bool(ex_data.safety_tags),
                    **ex_data.model_dump(),
                )
                examples.append(ex)
            except Exception as e:
                errors.append(f"Row {i}: {e}")

        await self.example_repo.bulk_create(examples)
        await self.repo.bump_version(ds)
        return DatasetImportResponse(imported=len(examples), skipped=0, errors=errors)

    def _to_response(self, ds: Dataset, example_count: int) -> DatasetResponse:
        return DatasetResponse(
            **{c.name: getattr(ds, c.name) for c in ds.__table__.columns},
            example_count=example_count,
        )

    def _example_to_response(self, ex: Example) -> ExampleResponse:
        return ExampleResponse(
            **{c.name: getattr(ex, c.name) for c in ex.__table__.columns}
        )
