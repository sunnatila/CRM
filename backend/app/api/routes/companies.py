from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.company import Company
from app.schemas.company import CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyOut])
async def list_companies(
    source: str | None = Query(default=None),
    q: str | None = Query(default=None, description="substring match on company name"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Company]:
    stmt = select(Company).order_by(Company.id).limit(limit).offset(offset)
    if source:
        stmt = stmt.where(Company.source == source)
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{company_id}", response_model=CompanyOut)
async def get_company(company_id: int, session: AsyncSession = Depends(get_session)) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    return company
