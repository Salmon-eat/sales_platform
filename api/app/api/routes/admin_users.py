"""Staff whitelist (admin spec §1, §2 "Користувачі"): emails allowed to sign in, roles, access switch."""

import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.api.deps import SessionDep, require_admin
from app.models import User, UserRole, UserSession
from app.services.auth import revoke_all

router = APIRouter(prefix="/admin/users", tags=["admin: users"])
log = logging.getLogger("bazarcito.admin")

Admin = Annotated[User, Depends(require_admin)]
StaffRole = Literal["manager", "admin"]
STAFF_ROLES = (UserRole.MANAGER, UserRole.ADMIN)


class AdminUser(BaseModel):
    id: int
    email: str | None
    name: str | None
    avatar: str | None
    role: UserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    active_sessions: int


class AdminUserCreate(BaseModel):
    email: EmailStr
    name: str | None = Field(None, max_length=200)
    role: StaffRole = "manager"


class AdminUserUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    role: StaffRole | None = None
    is_active: bool | None = None


async def _out(session: SessionDep, users: list[User]) -> list[AdminUser]:
    now = datetime.now(UTC)
    counts = dict(
        (
            await session.execute(
                select(UserSession.user_id, func.count())
                .where(
                    UserSession.user_id.in_([u.id for u in users]),
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > now,
                )
                .group_by(UserSession.user_id)
            )
        ).all()
    )
    return [
        AdminUser(
            id=u.id,
            email=u.email,
            name=u.name,
            avatar=u.avatar,
            role=u.role,
            is_active=u.is_active,
            last_login_at=u.last_login_at,
            created_at=u.created_at,
            active_sessions=counts.get(u.id, 0),
        )
        for u in users
    ]


async def _staff(session: SessionDep, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None or user.role not in STAFF_ROLES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("", response_model=list[AdminUser])
async def list_users(_: Admin, session: SessionDep) -> list[AdminUser]:
    users = (
        await session.scalars(
            select(User).where(User.role.in_(STAFF_ROLES)).order_by(User.is_active.desc(), User.email)
        )
    ).all()
    return await _out(session, list(users))


@router.post("", response_model=AdminUser, status_code=status.HTTP_201_CREATED)
async def add_user(body: AdminUserCreate, admin: Admin, session: SessionDep) -> AdminUser:
    """Put an email on the whitelist; the person signs in with the Google account of that email."""
    email = body.email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email_exists")
    user = User(email=email, name=body.name, role=UserRole(body.role), is_active=True)
    session.add(user)
    await session.commit()
    log.info("admin_id=%s added staff user_id=%s role=%s", admin.id, user.id, user.role)
    return (await _out(session, [user]))[0]


@router.patch("/{user_id}", response_model=AdminUser)
async def update_user(user_id: int, body: AdminUserUpdate, admin: Admin, session: SessionDep) -> AdminUser:
    user = await _staff(session, user_id)
    # an admin cannot lock themselves out
    if user.id == admin.id and (body.is_active is False or (body.role and body.role != "admin")):
        raise HTTPException(status.HTTP_409_CONFLICT, "cannot_change_self")
    if body.name is not None:
        user.name = body.name.strip() or None
    if body.role is not None:
        user.role = UserRole(body.role)
    switched_off = body.is_active is False and user.is_active
    if body.is_active is not None:
        user.is_active = body.is_active
    await session.commit()
    if switched_off:
        await revoke_all(session, user.id)  # access ends now, not when the session expires
    log.info("admin_id=%s updated staff user_id=%s %s", admin.id, user.id, body.model_dump(exclude_none=True))
    return (await _out(session, [user]))[0]


@router.post("/{user_id}/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(user_id: int, admin: Admin, session: SessionDep) -> None:
    user = await _staff(session, user_id)
    count = await revoke_all(session, user.id)
    log.info("admin_id=%s signed out user_id=%s sessions=%s", admin.id, user.id, count)
