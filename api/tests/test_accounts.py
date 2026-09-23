import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.services import accounts


class FakeRedis:
    """Enough of Redis for the sign-in code: a hash with a time to live."""

    def __init__(self):
        self.data: dict[str, dict[str, str]] = {}
        self.ttls: dict[str, int] = {}
        self.counters: dict[str, int] = {}

    async def ttl(self, key):
        return self.ttls.get(key, -2)

    async def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key, seconds):
        self.ttls[key] = seconds

    async def hset(self, key, mapping):
        self.data[key] = {k: str(v) for k, v in mapping.items()}

    async def hgetall(self, key):
        return self.data.get(key, {})

    async def hincrby(self, key, field, amount):
        row = self.data.setdefault(key, {})
        row[field] = str(int(row.get(field, 0)) + amount)

    async def delete(self, key):
        self.data.pop(key, None)
        self.ttls.pop(key, None)


def code_from(sent: list[tuple[str, str, str]]) -> str:
    return "".join(ch for ch in sent[-1][2] if ch.isdigit())[:6]


@pytest.fixture
def letters(monkeypatch):
    sent: list[tuple[str, str, str]] = []

    async def fake_send(to, subject, text):
        sent.append((to, subject, text))
        return True

    monkeypatch.setattr(accounts.mail, "send", fake_send)
    return sent


async def test_code_arrives_and_opens_the_account(letters):
    redis = FakeRedis()
    await accounts.send_code(redis, "Olena@Example.com ", "uk")
    assert letters[-1][0] == "olena@example.com"
    assert "Ваш код" in letters[-1][2]
    await accounts.check_code(redis, "olena@example.com", code_from(letters))
    # the code works once
    with pytest.raises(HTTPException) as error:
        await accounts.check_code(redis, "olena@example.com", code_from(letters))
    assert error.value.detail == "code_expired"


async def test_a_wrong_code_is_refused_and_guessing_is_capped(letters):
    redis = FakeRedis()
    await accounts.send_code(redis, "olena@example.com", "es")
    for _ in range(accounts.MAX_TRIES):
        with pytest.raises(HTTPException) as error:
            await accounts.check_code(redis, "olena@example.com", "000000")
        assert error.value.status_code == 400
    with pytest.raises(HTTPException) as error:
        await accounts.check_code(redis, "olena@example.com", code_from(letters))
    assert error.value.status_code == 429  # even the right code no longer helps


async def test_a_new_code_cannot_be_asked_for_every_second(letters):
    redis = FakeRedis()
    await accounts.send_code(redis, "olena@example.com", "es")
    with pytest.raises(HTTPException) as error:
        await accounts.send_code(redis, "olena@example.com", "es")
    assert error.value.detail == "wait_before_resend"


def sign(data: dict, token: str) -> str:
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hashlib.sha256(token.encode()).digest()
    return hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()


def test_only_telegram_can_sign_the_sign_in(monkeypatch):
    monkeypatch.setattr(accounts.settings, "telegram_login_token", "12345:test-token")
    user = {"id": 7, "first_name": "Olena", "auth_date": int(time.time())}
    accounts.check_telegram({**user, "hash": sign(user, "12345:test-token")})

    for bad in ({**user, "hash": "0" * 64}, {**user, "hash": sign(user, "another-token")}):
        with pytest.raises(HTTPException) as error:
            accounts.check_telegram(bad)
        assert error.value.detail == "invalid_token"

    old = {**user, "auth_date": int(time.time()) - accounts.TELEGRAM_MAX_AGE - 60}
    with pytest.raises(HTTPException) as error:
        accounts.check_telegram({**old, "hash": sign(old, "12345:test-token")})
    assert error.value.detail == "expired_token"


def test_telegram_sign_in_is_off_without_a_bot(monkeypatch):
    monkeypatch.setattr(accounts.settings, "telegram_login_token", "")
    with pytest.raises(HTTPException) as error:
        accounts.check_telegram({"id": 1, "auth_date": 1, "hash": "x" * 64})
    assert error.value.status_code == 503


async def test_the_letter_is_written_in_the_visitors_language(letters):
    redis = FakeRedis()
    for lang, expected in (("es", "Tu código"), ("en", "Your code"), ("ru", "Ваш код")):
        redis.ttls.clear()
        await accounts.send_code(redis, f"{lang}@example.com", lang)
        assert expected in letters[-1][2]
