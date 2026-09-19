import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.api.routes import bot_sync
from app.schemas.bot_sync import BotSyncIn
from app.services.telegram import _phone, bot_status, site_status


def creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_bot_statuses_map_to_the_site_and_back():
    assert [site_status(s) for s in ("new", "in_work", "waiting", "done")] == [
        "new",
        "in_progress",
        "in_progress",
        "done",
    ]
    # "rejected" has no match in the bot: it becomes "done" there and must stay "rejected" here
    assert bot_status("rejected") == "done"
    assert bot_status("in_progress") == "in_work"


def test_phones_typed_in_the_bot_are_kept_when_not_valid():
    assert _phone("+34 612 345 678") == "+34612345678"
    assert _phone("мій номер 12") == "мій номер 12"
    assert _phone("") is None


def test_endpoints_are_closed_without_the_setting(monkeypatch):
    monkeypatch.setattr(bot_sync.settings, "bot_sync_token", "")
    with pytest.raises(HTTPException) as error:
        bot_sync.require_bot(creds("anything"))
    assert error.value.status_code == 404


def test_only_the_right_token_passes(monkeypatch):
    monkeypatch.setattr(bot_sync.settings, "bot_sync_token", "s" * 40)
    bot_sync.require_bot(creds("s" * 40))
    for wrong in (creds("x" * 40), None):
        with pytest.raises(HTTPException) as error:
            bot_sync.require_bot(wrong)
        assert error.value.status_code == 401


def test_a_sync_batch_is_limited():
    message = {
        "id": 1,
        "client_id": 1,
        "app_id": 1001,
        "direction": "client",
        "content_type": "text",
        "text": "hi",
        "delivery": "internal",
        "created_at": "2026-09-19T10:00:00",
    }
    BotSyncIn(messages=[message] * 500)
    with pytest.raises(ValidationError):
        BotSyncIn(messages=[message] * 501)
    with pytest.raises(ValidationError):
        BotSyncIn(messages=[{**message, "direction": "system"}])
