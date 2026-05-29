from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        result = await self.session.get(self.model, id)
        return result

    async def list(
        self,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        q = select(self.model)
        count_q = select(func.count()).select_from(self.model)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    q = q.where(getattr(self.model, key) == value)
                    count_q = count_q.where(getattr(self.model, key) == value)

        total = (await self.session.execute(count_q)).scalar_one()
        rows = (await self.session.execute(q.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def create(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def flush(self) -> None:
        await self.session.flush()
