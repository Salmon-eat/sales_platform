import secrets
from typing import Annotated

from fastapi import APIRouter, Path, Request, status

from app.api.deps import RedisDep, SessionDep
from app.schemas.application import ApplicationCreated, ApplicationIn, ChatMessageIn, ChatMessageOut
from app.services import antibot
from app.services.applications import add_visitor_message, chat_by_token, chat_messages, create_application

router = APIRouter(prefix="/applications", tags=["applications"])
chat_router = APIRouter(prefix="/chat", tags=["site chat"])

Token = Annotated[str, Path(min_length=20, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


@chat_router.get("/{token}", response_model=list[ChatMessageOut])
async def read_chat(token: Token, session: SessionDep) -> list[ChatMessageOut]:
    """The visitor's conversation with the managers (the token lives only in their browser)."""
    application = await chat_by_token(session, token)
    return [
        ChatMessageOut.model_validate(m, from_attributes=True)
        for m in await chat_messages(session, application.id)
    ]


@chat_router.post("/{token}", response_model=list[ChatMessageOut], status_code=status.HTTP_201_CREATED)
async def write_chat(
    token: Token, body: ChatMessageIn, session: SessionDep, redis: RedisDep
) -> list[ChatMessageOut]:
    application = await chat_by_token(session, token)
    await add_visitor_message(session, redis, application, body.text)
    return [
        ChatMessageOut.model_validate(m, from_attributes=True)
        for m in await chat_messages(session, application.id)
    ]


@router.post("", response_model=ApplicationCreated, status_code=status.HTTP_201_CREATED)
async def submit_application(
    body: ApplicationIn, request: Request, session: SessionDep, redis: RedisDep
) -> ApplicationCreated:
    """Application without registration: a listing, a category, or just "call me about work"."""
    ip = request.client.host if request.client else None
    if antibot.is_honeypot(body.website):
        # looks accepted, stores nothing: the bot does not learn it was caught
        antibot.log.info("honeypot: application from %s dropped", ip)
        return ApplicationCreated(
            id=0, duplicate=False, chat_token=secrets.token_urlsafe(24) if body.channel == "chat" else None
        )
    await antibot.require_human(body.captcha, ip)
    return await create_application(session, redis, body, ip)
