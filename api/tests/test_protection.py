import httpx
import pytest
from fastapi import HTTPException

from app import main
from app.core import ratelimit
from app.schemas.application import ApplicationIn
from app.services import antibot


class FakePipeline:
    def __init__(self, store: dict[str, int]):
        self.store, self.ops = store, []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def incr(self, key):
        self.ops.append(key)

    def expire(self, key, seconds, nx=False):
        pass

    async def execute(self):
        key = self.ops[0]
        self.store[key] = self.store.get(key, 0) + 1
        return [self.store[key], True]


class FakeRedis:
    def __init__(self):
        self.store: dict[str, int] = {}

    def pipeline(self, transaction=False):
        return FakePipeline(self.store)


def client(ip: str) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=main.app, client=(ip, 5000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def test_private_addresses_are_our_own_servers():
    assert ratelimit.is_internal("172.18.0.5")
    assert ratelimit.is_internal("127.0.0.1")
    assert not ratelimit.is_internal("88.12.34.56")
    assert not ratelimit.is_internal("2a02:9130::1")


def test_rules_pick_the_strictest_matching_bucket():
    assert ratelimit.rule_for("/v1/applications", "POST") == ("/v1/applications:w", 10)
    assert ratelimit.rule_for("/v1/applications", "GET") == ("/v1/:a", 240)
    assert ratelimit.rule_for("/v1/chat/abc", "GET") == ("/v1/chat/:a", 30)
    assert ratelimit.rule_for("/v1/health", "GET") is None
    assert ratelimit.rule_for("/v1/internal/bot/sync", "POST") is None


async def test_a_flood_from_one_address_gets_429(monkeypatch):
    monkeypatch.setattr(main, "redis", FakeRedis())
    monkeypatch.setattr(ratelimit, "RULES", (("/v1/", None, 3),))
    async with client("88.12.34.56") as outside:
        codes = [(await outside.get("/v1/auth/config")).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    async with client("91.1.1.1") as someone_else:
        assert (await someone_else.get("/v1/auth/config")).status_code == 200
    async with client("172.18.0.5") as our_web_server:
        assert all([(await our_web_server.get("/v1/auth/config")).status_code == 200 for _ in range(5)])


async def test_private_answers_are_not_cached(monkeypatch):
    monkeypatch.setattr(main, "redis", FakeRedis())
    async with client("88.12.34.56") as outside:
        response = await outside.get("/v1/auth/config")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_honeypot():
    assert antibot.is_honeypot("http://spam.example")
    assert not antibot.is_honeypot(None)
    assert not antibot.is_honeypot("  ")
    form = ApplicationIn(name="Olena", phone="612345678", lang="uk", consent=True, website="x")
    assert form.website == "x"


async def test_turnstile_is_required_only_when_switched_on(monkeypatch):
    monkeypatch.setattr(antibot.settings, "turnstile_secret_key", "")
    await antibot.require_human(None, "1.2.3.4")  # off: passes

    monkeypatch.setattr(antibot.settings, "turnstile_secret_key", "secret")
    with pytest.raises(HTTPException) as error:
        await antibot.require_human(None, "1.2.3.4")
    assert error.value.detail == "captcha"

    monkeypatch.setattr(antibot, "_verify", lambda token, ip: token == "good")
    await antibot.require_human("good", "1.2.3.4")
    with pytest.raises(HTTPException):
        await antibot.require_human("forged", "1.2.3.4")

    def unreachable(token, ip):
        raise OSError("timeout")

    monkeypatch.setattr(antibot, "_verify", unreachable)
    await antibot.require_human("any", "1.2.3.4")  # Cloudflare down: a person's application is not lost
