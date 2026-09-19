from fastapi import APIRouter

from app.api.deps import RedisDep, SessionDep
from app.core.config import settings
from app.schemas.common import Lang
from app.schemas.taxonomy import TaxonomyOut
from app.services.cache import cached
from app.services.taxonomy import build_taxonomy

router = APIRouter(tags=["taxonomy"])


@router.get("/taxonomy", response_model=TaxonomyOut)
async def taxonomy(session: SessionDep, redis: RedisDep, lang: Lang = "es") -> TaxonomyOut:
    """Sections -> sectors -> professions with effective (own + inherited) attributes."""
    return await cached(
        redis,
        "taxonomy",
        {"lang": lang},
        settings.taxonomy_cache_ttl,
        TaxonomyOut,
        lambda: build_taxonomy(session, lang),
    )
