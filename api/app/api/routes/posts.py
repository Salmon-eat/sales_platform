"""The blog: what people search for before they search for an ad.

Public reading here; writing is in the admin. One article is one language — never a machine
translation of another one.
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from app.api.deps import AdminLang, SessionDep, require_staff
from app.core.slug import slugify
from app.models import Post, User
from app.models.post import MAX_BODY
from app.schemas.common import Lang

router = APIRouter(tags=["blog"])
admin_router = APIRouter(prefix="/admin/posts", tags=["admin: blog"])

Staff = Annotated[User, Depends(require_staff)]


class PostIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    lang: Lang = "es"
    excerpt: str = Field("", max_length=300)
    body: str = Field("", max_length=MAX_BODY)
    cover: str | None = Field(None, max_length=200)
    status: Literal["draft", "published"] = "draft"
    # left empty: made from the title
    slug: str | None = Field(None, max_length=160, pattern=r"^[a-z0-9-]*$")

    @field_validator("title", "excerpt", "body")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


def _out(post: Post, full: bool = False) -> dict[str, Any]:
    data = {
        "id": post.id,
        "slug": post.slug,
        "lang": post.lang,
        "title": post.title,
        "excerpt": post.excerpt,
        "cover": post.cover,
        "status": post.status,
        "published_at": post.published_at,
        "updated_at": post.updated_at,
    }
    if full:
        data["body"] = post.body
    return data


@router.get("/posts")
async def list_posts(
    session: SessionDep,
    lang: Lang = "es",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 12,
) -> dict[str, Any]:
    conds = [Post.status == "published", Post.lang == lang]
    total = await session.scalar(select(func.count()).select_from(Post).where(*conds)) or 0
    rows = (
        await session.scalars(
            select(Post)
            .where(*conds)
            .order_by(Post.published_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return {"items": [_out(row) for row in rows], "total": total, "page": page, "per_page": per_page}


@router.get("/posts/{slug}")
async def one_post(slug: str, session: SessionDep, lang: Lang = "es") -> dict[str, Any]:
    post = await session.scalar(
        select(Post).where(Post.slug == slug, Post.lang == lang, Post.status == "published")
    )
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    return _out(post, full=True)


# ---------------------------------------------------------------------------- the admin side


@admin_router.get("")
async def all_posts(session: SessionDep, user: Staff, lang: AdminLang) -> list[dict[str, Any]]:
    rows = await session.scalars(select(Post).order_by(Post.updated_at.desc()).limit(200))
    return [_out(row) for row in rows]


@admin_router.get("/{post_id}")
async def get_post(post_id: int, session: SessionDep, user: Staff) -> dict[str, Any]:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    return _out(post, full=True)


async def _free_slug(session: SessionDep, wanted: str, lang: str, post_id: int | None) -> str:
    base = (wanted or "post")[:150]
    candidate = base
    for suffix in range(2, 60):
        clash = await session.scalar(
            select(Post.id).where(Post.slug == candidate, Post.lang == lang, Post.id != (post_id or 0))
        )
        if clash is None:
            return candidate
        candidate = f"{base}-{suffix}"
    return f"{base}-{datetime.now(UTC):%Y%m%d%H%M%S}"


@admin_router.post("", status_code=status.HTTP_201_CREATED)
async def create_post(body: PostIn, session: SessionDep, user: Staff) -> dict[str, Any]:
    post = Post(author_id=user.id)
    await _fill(session, post, body)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return _out(post, full=True)


@admin_router.put("/{post_id}")
async def update_post(post_id: int, body: PostIn, session: SessionDep, user: Staff) -> dict[str, Any]:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    await _fill(session, post, body)
    await session.commit()
    await session.refresh(post)
    return _out(post, full=True)


async def _fill(session: SessionDep, post: Post, data: PostIn) -> None:
    post.title, post.lang = data.title, data.lang
    post.excerpt, post.body, post.cover = data.excerpt, data.body, data.cover
    wanted = data.slug or slugify(data.title, data.lang)
    post.slug = await _free_slug(session, wanted, data.lang, post.id)
    if data.status == "published" and post.status != "published":
        post.published_at = post.published_at or datetime.now(UTC)
    post.status = data.status


@admin_router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, session: SessionDep, user: Staff) -> None:
    post = await session.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    await session.delete(post)
    await session.commit()
