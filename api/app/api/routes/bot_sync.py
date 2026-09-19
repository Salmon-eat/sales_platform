import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import SessionDep
from app.core.config import settings
from app.schemas.bot_sync import BotOutgoingItem, BotSyncIn, BotSyncOut
from app.services.telegram import outgoing, sync_from_bot

_bearer = HTTPBearer(auto_error=False)


def require_bot(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Only the Telegram bot, with the shared BOT_SYNC_TOKEN; without it the endpoints do not exist."""
    if not settings.bot_sync_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    given = credentials.credentials if credentials else ""
    if not hmac.compare_digest(given.encode(), settings.bot_sync_token.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


router = APIRouter(prefix="/internal/bot", tags=["telegram bot"], dependencies=[Depends(require_bot)])


@router.post("/sync", response_model=BotSyncOut)
async def sync(body: BotSyncIn, session: SessionDep) -> BotSyncOut:
    """New and changed applications, new messages and topic links from the bot; safe to send twice."""
    return await sync_from_bot(session, body)


@router.get("/outgoing", response_model=list[BotOutgoingItem])
async def pending_for_bot(
    session: SessionDep, after: Annotated[int, Query(ge=0, description="the last id the bot has taken")] = 0
) -> list[BotOutgoingItem]:
    """Replies and status changes made in the admin, in order; the bot remembers the last id it took."""
    return await outgoing(session, after)
