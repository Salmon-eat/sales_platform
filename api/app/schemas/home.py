from pydantic import BaseModel, Field

from app.schemas.listing import ListingCard


class HomeTotals(BaseModel):
    listings: int
    today: int = Field(description="published in the last 24 hours")
    sections: int


class HomeSection(BaseModel):
    key: str
    slug: str
    name: str
    count: int
    categories: list[dict[str, str]] = Field(description="a few category names shown under the section")


class HomeOut(BaseModel):
    totals: HomeTotals
    sections: list[HomeSection]
    fresh: list[ListingCard]
