"""Load test of GET /v1/listings (list + facets) — spec §11 stage 3: p95 < 300 ms on 10k listings.

    python -m app.loadtest --base http://localhost:8000 --requests 600 --concurrency 8

Scenarios mix what real pages do: no filters, text queries (incl. typos and Cyrillic), professions,
cities with radius, tier-2 combinations, CE attributes, sorting and deep pages. `--cold` bumps the
cache version before every request, so facets are computed each time (worst case).
"""

import argparse
import asyncio
import random
import statistics
import time
from collections import defaultdict

import httpx
from redis.asyncio import Redis

from app.core.config import settings
from app.services.cache import CACHE_VERSION_KEY

CITIES = [
    "madrid",
    "barcelona",
    "valencia",
    "sevilla",
    "malaga",
    "murcia",
    "zaragoza",
    "alicante",
    "bilbao",
    "almeria",
]
QUERIES = ["водій", "водитель фура", "conductor ce", "camarero", "кухар", "прибирання", "almacen", "carretillero",  # noqa: E501
           "збір фруктів", "plytochnyk", "camarrero", "водій се мадрид", "limpieza hoteles", "будівельник"]  # fmt: skip  # noqa: E501
PROFESSIONS = ["vodii-ce", "ofitsiant", "kukhar", "robitnyk-skladu", "zbir-fruktiv", "prybyrannia-hoteliv"]


def scenario(rng: random.Random) -> tuple[str, dict[str, str]]:
    base = {"lang": "uk", "section": "empleo", "per_page": "20"}
    kind = rng.choice(["plain", "q", "profession", "city_radius", "tier2", "ce_attrs", "sort_page"])
    p = dict(base)
    if kind == "q":
        p["q"] = rng.choice(QUERIES)
    elif kind == "profession":
        p["category"] = rng.choice(PROFESSIONS)
        p["location"] = rng.choice(CITIES)
    elif kind == "city_radius":
        p["location"] = rng.choice(CITIES)
        p["radius"] = rng.choice(["10", "25", "50", "100"])
    elif kind == "tier2":
        p["housing"] = "1"
        p["salary_min"] = rng.choice(["1200", "1500", "2000"])
        p["schedule"] = rng.choice(["full", "full,shifts", "part"])
        if rng.random() < 0.5:
            p["no_language"] = "1"
    elif kind == "ce_attrs":
        p["category"] = "vodii-ce"
        p["a.trailer_type"] = rng.choice(["frigorifico", "lona,frigorifico", "cisterna"])
        if rng.random() < 0.5:
            p["a.adr"] = "1"
    elif kind == "sort_page":
        p["sort"] = rng.choice(["salary", "new"])
        p["page"] = str(rng.randint(2, 20))
    return kind, p


async def run(base: str, total: int, concurrency: int, cold: bool, seed: int) -> None:
    rng = random.Random(seed)
    plan = [scenario(rng) for _ in range(total)]
    latencies: dict[str, list[float]] = defaultdict(list)
    errors = 0
    redis = Redis.from_url(settings.redis_url) if cold else None
    queue: asyncio.Queue = asyncio.Queue()
    for item in plan:
        queue.put_nowait(item)

    async def worker(client: httpx.AsyncClient) -> None:
        nonlocal errors
        while not queue.empty():
            kind, params = queue.get_nowait()
            if redis:
                await redis.incr(CACHE_VERSION_KEY)
            start = time.perf_counter()
            response = await client.get(f"{base}/v1/listings", params=params)
            elapsed = (time.perf_counter() - start) * 1000
            if response.status_code != 200:
                errors += 1
            latencies[kind].append(elapsed)
            latencies["ALL"].append(elapsed)

    async with httpx.AsyncClient(timeout=30) as client:
        await client.get(f"{base}/v1/listings", params={"lang": "uk"})  # warm up the process
        started = time.perf_counter()
        await asyncio.gather(*(worker(client) for _ in range(concurrency)))
        wall = time.perf_counter() - started
    if redis:
        await redis.aclose()

    def pct(values: list[float], p: float) -> float:
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1))))]

    print(f"{'scenario':<12} {'n':>5} {'p50':>7} {'p95':>7} {'p99':>7} {'max':>7}   (ms)")
    for kind in sorted(latencies, key=lambda k: (k != "ALL", k)):
        v = latencies[kind]
        p50, p95, p99 = statistics.median(v), pct(v, 95), pct(v, 99)
        print(f"{kind:<12} {len(v):>5} {p50:>7.0f} {p95:>7.0f} {p99:>7.0f} {max(v):>7.0f}")
    rate = total / wall
    print(
        f"\n{total} requests, concurrency {concurrency}, {rate:.0f} req/s, errors: {errors}, cold cache: {cold}"  # noqa: E501
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.loadtest")
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=600)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument(
        "--cold", action="store_true", help="invalidate the facets cache before every request"
    )
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    asyncio.run(run(args.base, args.requests, args.concurrency, args.cold, args.seed))


if __name__ == "__main__":
    main()
