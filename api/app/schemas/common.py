from math import ceil
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, computed_field

# Internal language codes are ISO 639-1 ("uk" = Ukrainian); the website shows Ukrainian under /ua/.
Lang = Literal["es", "en", "uk", "ru"]
LANGS: tuple[str, ...] = ("es", "en", "uk", "ru")

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    per_page: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        return ceil(self.total / self.per_page) if self.total else 0
