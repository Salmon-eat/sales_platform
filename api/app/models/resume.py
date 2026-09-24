"""The candidate's own CV: filled in once, sent with one press afterwards."""

from typing import Any

from sqlalchemy import Boolean, ForeignKey, LargeBinary, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# what a person can say about a language, from "a few words" to "my own"
LANGUAGE_LEVELS = ("a1", "a2", "b1", "b2", "c1", "native")
# what counts on a Spanish building site or behind a wheel
LICENCES = ("b", "c", "ce", "d", "code95", "adr", "forklift", "crane")
MAX_ABOUT = 3000


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    about: Mapped[str] = mapped_column(Text, default="", server_default="")
    city_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    relocate: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    experience_years: Mapped[int | None] = mapped_column(SmallInteger)
    languages: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    licences: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    has_car: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    work_permit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    schedule: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    salary_min: Mapped[int | None]
    salary_period: Mapped[str | None] = mapped_column(String(10))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # the attached file, kept here and never in the public media folder
    file_name: Mapped[str | None] = mapped_column(String(200))
    file_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None]
    file_data: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)

    @property
    def has_file(self) -> bool:
        return self.file_name is not None
