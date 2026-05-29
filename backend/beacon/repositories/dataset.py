from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.dataset import Dataset, Example
from beacon.repositories.base import BaseRepository


class DatasetRepository(BaseRepository[Dataset]):
    model = Dataset

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_program(
        self, program_id: UUID, limit: int = 20, offset: int = 0
    ) -> tuple[list[Dataset], int]:
        count_q = (
            select(func.count())
            .select_from(Dataset)
            .where(Dataset.program_id == program_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()
        q = (
            select(Dataset)
            .where(Dataset.program_id == program_id)
            .order_by(Dataset.name)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return list(rows), total

    async def bump_version(self, dataset: Dataset) -> Dataset:
        dataset.version += 1
        await self.session.flush()
        return dataset

    async def get_example_count(self, dataset_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Example)
            .where(Example.dataset_id == dataset_id)
        )
        return result.scalar_one()


class ExampleRepository(BaseRepository[Example]):
    model = Example

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_dataset(
        self,
        dataset_id: UUID,
        limit: int = 50,
        offset: int = 0,
        difficulty: str | None = None,
        persona: str | None = None,
    ) -> tuple[list[Example], int]:
        filters = [Example.dataset_id == dataset_id]
        if difficulty:
            filters.append(Example.difficulty == difficulty)
        if persona:
            filters.append(Example.persona == persona)

        count_q = select(func.count()).select_from(Example)
        q = select(Example)
        for f in filters:
            count_q = count_q.where(f)
            q = q.where(f)

        total = (await self.session.execute(count_q)).scalar_one()
        rows = (
            await self.session.execute(q.order_by(Example.created_at).offset(offset).limit(limit))
        ).scalars().all()
        return list(rows), total

    async def bulk_create(self, examples: list[Example]) -> list[Example]:
        for ex in examples:
            self.session.add(ex)
        await self.session.flush()
        return examples
