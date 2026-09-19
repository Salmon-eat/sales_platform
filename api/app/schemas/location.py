from pydantic import BaseModel


class LocationRef(BaseModel):
    level: str
    slug: str
    name: str


class LocationOut(BaseModel):
    id: int
    level: str
    slug: str
    name: str
    ine_code: str | None
    population: int | None
    lat: float | None
    lon: float | None
    parents: list[LocationRef]


class AdminLocation(BaseModel):
    id: int
    level: str
    slug: str
    ine_code: str | None
    names: dict[str, str]
    aliases: list[str]
    population: int | None
    lat: float | None
    lon: float | None
    parent_name: str | None
