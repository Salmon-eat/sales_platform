"""Orders in the admin: what people bought, and marking a transfer as received.

Marking an order paid by hand is how a bank transfer is handled, and the only way to sell anything at
all until the card account exists. It is an admin's job, not a manager's.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep, require_admin, require_staff
from app.models import Order, User
from app.services import payments
from app.services.cache import bump_cache_version

router = APIRouter(prefix="/admin/orders", tags=["admin: orders"])

Staff = Annotated[User, Depends(require_staff)]
Admin = Annotated[User, Depends(require_admin)]


class PaidIn(BaseModel):
    note: str | None = Field(None, max_length=200, description="transfer reference, who confirmed it")


@router.get("")
async def orders(
    session: SessionDep,
    user: Staff,
    status_: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict[str, Any]]:
    conds = [Order.status == status_] if status_ else []
    rows = (
        await session.scalars(
            select(Order).where(*conds).order_by(Order.created_at.desc()).limit(limit)
        )
    ).all()
    out = []
    for order in rows:
        buyer = await session.get(User, order.user_id) if order.user_id else None
        out.append(
            {
                "id": order.id,
                "product": order.product,
                "days": order.days,
                "amount": order.amount,
                "currency": order.currency,
                "status": order.status,
                "provider": order.provider,
                "listing_id": order.listing_id,
                "company_id": order.company_id,
                "buyer": (buyer.name or buyer.email) if buyer else None,
                "note": order.note,
                "created_at": order.created_at,
                "paid_at": order.paid_at,
            }
        )
    return out


@router.post("/{order_id}/paid", status_code=204)
async def mark_paid(
    order_id: int, body: PaidIn, session: SessionDep, redis: RedisDep, user: Admin
) -> None:
    """The money arrived some other way (a transfer, cash): switch the extra on."""
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    if order.status == "paid":
        raise HTTPException(status.HTTP_409_CONFLICT, "already_paid")
    order.note = body.note
    await payments.mark_paid(session, order, "manual", f"staff:{user.id}")
    await bump_cache_version(redis)


@router.post("/{order_id}/cancel", status_code=204)
async def cancel(order_id: int, session: SessionDep, user: Admin) -> None:
    order = await session.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    if order.status == "paid":
        raise HTTPException(status.HTTP_409_CONFLICT, "already_paid")
    order.status = "cancelled"
    await session.commit()
