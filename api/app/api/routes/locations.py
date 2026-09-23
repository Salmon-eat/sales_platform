from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Location
from app.models.i18n import tr
from app.schemas.common import Lang
from app.schemas.location import LocationOut, LocationRef
from app.services.locations import coords

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/popular", response_model=list[LocationRef])
async def popular(
    session: SessionDep,
    lang: Lang = "es",
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
) -> list[LocationRef]:
    """Municipalities for filters and navigation.

    TODO(stage 3): cities with active listings first, then by population (spec §3, §9).
    """
    rows = await session.scalars(
        select(Location)
        .where(Location.level == "municipio")
        .order_by(Location.population.desc().nulls_last())
        .limit(limit)
    )
    return [LocationRef(id=r.id, level=r.level, slug=r.slug, name=tr(r.names, lang)) for r in rows]


@router.get("/{slug}", response_model=LocationOut)
async def get_location(
    slug: Annotated[str, Path(pattern=r"^[a-z0-9-]{1,120}$")],
    session: SessionDep,
    lang: Lang = "es",
) -> LocationOut:
    lat, lon = coords()
    row = (await session.execute(select(Location, lat, lon).where(Location.slug == slug))).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")
    location, lat_value, lon_value = row

    parents: list[LocationRef] = []
    parent_id = location.parent_id
    while parent_id is not None:
        parent = await session.get(Location, parent_id)
        if parent is None:
            break
        parents.insert(0, LocationRef(level=parent.level, slug=parent.slug, name=tr(parent.names, lang)))
        parent_id = parent.parent_id

    return LocationOut(
        id=location.id,
        level=location.level,
        slug=location.slug,
        name=tr(location.names, lang),
        ine_code=location.ine_code,
        population=location.population,
        lat=lat_value,
        lon=lon_value,
        parents=parents,
    )
