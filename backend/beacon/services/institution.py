import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from beacon.models.institution import Institution, Program
from beacon.repositories.institution import InstitutionRepository, ProgramRepository
from beacon.schemas.institution import (
    InstitutionCreate, InstitutionResponse, InstitutionUpdate,
    ProgramCreate, ProgramResponse, ProgramUpdate,
)
from beacon.schemas.base import PaginatedResponse


class InstitutionService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = InstitutionRepository(session)

    async def list(self, limit: int = 20, offset: int = 0) -> PaginatedResponse[InstitutionResponse]:
        rows, total = await self.repo.list_with_counts(limit=limit, offset=offset)
        items = []
        for inst, program_count in rows:
            items.append(InstitutionResponse(
                **{c.name: getattr(inst, c.name) for c in inst.__table__.columns},
                program_count=program_count,
            ))
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get(self, institution_id: uuid.UUID) -> InstitutionResponse:
        inst = await self.repo.get_by_id(institution_id)
        if not inst:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
        return InstitutionResponse(
            **{c.name: getattr(inst, c.name) for c in inst.__table__.columns},
            program_count=0,
        )

    async def create(self, data: InstitutionCreate) -> InstitutionResponse:
        existing = await self.repo.get_by_slug(data.slug)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
        if data.ipeds_id:
            existing_ipeds = await self.repo.get_by_ipeds(data.ipeds_id)
            if existing_ipeds:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="IPEDS ID already registered")

        inst = Institution(**data.model_dump())
        inst = await self.repo.create(inst)
        return await self.get(inst.id)

    async def update(self, institution_id: uuid.UUID, data: InstitutionUpdate) -> InstitutionResponse:
        inst = await self.repo.get_by_id(institution_id)
        if not inst:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(inst, field, value)
        await self.repo.flush()
        return await self.get(inst.id)

    async def delete(self, institution_id: uuid.UUID) -> None:
        inst = await self.repo.get_by_id(institution_id)
        if not inst:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
        await self.repo.delete(inst)


class ProgramService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ProgramRepository(session)

    async def list(
        self, institution_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> PaginatedResponse[ProgramResponse]:
        rows, total = await self.repo.list_by_institution(institution_id, limit=limit, offset=offset)
        items = [self._to_response(p, skip_institution=True) for p in rows]
        return PaginatedResponse(
            items=items, total=total, limit=limit, offset=offset,
            has_more=(offset + limit) < total,
        )

    async def get(self, program_id: uuid.UUID) -> ProgramResponse:
        program = await self.repo.get_with_institution(program_id)
        if not program:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
        return self._to_response(program)

    async def create(self, data: ProgramCreate) -> ProgramResponse:
        program = Program(**data.model_dump())
        program = await self.repo.create(program)
        return await self.get(program.id)

    async def update(self, program_id: uuid.UUID, data: ProgramUpdate) -> ProgramResponse:
        program = await self.repo.get_by_id(program_id)
        if not program:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(program, field, value)
        await self.repo.flush()
        return await self.get(program.id)

    async def delete(self, program_id: uuid.UUID) -> None:
        program = await self.repo.get_by_id(program_id)
        if not program:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
        await self.repo.delete(program)

    def _to_response(self, p: Program, skip_institution: bool = False) -> ProgramResponse:
        from beacon.schemas.institution import InstitutionSummary
        data = {c.name: getattr(p, c.name) for c in p.__table__.columns}
        institution = None
        if not skip_institution:
            try:
                if p.institution:
                    institution = InstitutionSummary(id=p.institution.id, name=p.institution.name, slug=p.institution.slug)
            except Exception:
                pass
        return ProgramResponse(**data, institution=institution)
