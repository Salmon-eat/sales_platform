"""Side-by-side trial: the same ads, the same queries, Postgres against Meilisearch.

    docker compose --profile search up -d meilisearch
    docker compose exec api python scripts/search_engine_trial.py

Run it again whenever the question "should we move to a search engine?" comes back — the answer
depends on how many ads the site has, and the answer on 39 ads is not the answer on 50 000.


Nothing on the site talks to Meilisearch. This only answers one question: on OUR data, in OUR four
languages, does a real search engine find things our Postgres search does not?

The documents carry exactly what the Postgres search document carries — the ad in every language it
was written in, plus the category name and its synonyms — so what is being compared is the engine,
not the dictionary.
"""

import asyncio
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so it runs from anywhere

from sqlalchemy import text  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402

MEILI = "http://meilisearch:7700"
KEY = "dev-master-key"
INDEX = "listings"
API = "http://localhost:8000/v1/listings"

LANGS = ("es", "en", "uk", "ru")

QUERIES = [
    ("uk", "робота водієм"),
    ("uk", "прибирання"),
    ("uk", "квартира"),
    ("uk", "ноутбук"),
    ("uk", "ноутбукк"),          # a typo
    ("uk", "ноутбк"),            # a missing letter
    ("uk", "диван"),
    ("uk", "дiван"),             # latin i instead of cyrillic і
    ("uk", "холодильник"),
    ("uk", "велосипед"),
    ("uk", "айфон"),
    ("uk", "конductor"),         # half-typed, mixed alphabets
    ("uk", "фургон"),
    ("uk", "ліжечко"),
    ("ru", "работа водителем"),
    ("ru", "квартира"),
    ("ru", "ноутбук"),
    ("ru", "холодильник"),
    ("es", "sofa"),
    ("es", "sofá"),
    ("es", "portatil"),
    ("es", "portátil"),
    ("es", "conductr"),          # a typo
    ("es", "limpieza"),
    ("es", "piso madrid"),
    ("es", "furgonet"),          # half a word
    ("en", "laptop"),
    ("en", "driver job"),
    ("en", "apartment"),
    ("en", "cleaning"),
    ("en", "lapto"),             # half a word
]


def call(method: str, path: str, body: object = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        MEILI + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{method} {path} -> {exc.code} {exc.read().decode()[:400]}") from exc


def wait_for(task_uid: int) -> None:
    for _ in range(120):
        task = call("GET", f"/tasks/{task_uid}")
        if task["status"] in {"succeeded", "failed", "canceled"}:
            if task["status"] != "succeeded":
                raise SystemExit(f"task {task_uid}: {task['status']} {task.get('error')}")
            return
        time.sleep(0.5)
    raise SystemExit(f"task {task_uid} never finished")


DOCUMENTS_SQL = """
SELECT l.id,
       jsonb_object_agg(t.lang, t.title) AS titles,
       jsonb_object_agg(t.lang, concat_ws(' ', t.description, t.requirements, t.conditions)) AS bodies,
       c.name AS cat_name, c.synonyms AS cat_syn,
       p.name AS parent_name, p.synonyms AS parent_syn,
       m.names AS place_names
  FROM listings l
  JOIN listing_translations t ON t.listing_id = l.id
  JOIN categories c ON c.id = l.category_id
  LEFT JOIN categories p ON p.id = c.parent_id
  LEFT JOIN locations m ON m.id = l.location_id
 WHERE l.status = 'active'
 GROUP BY l.id, c.name, c.synonyms, p.name, p.synonyms, m.names
"""


def words_of(synonyms: dict | None) -> str:
    if not synonyms:
        return ""
    return " ".join(w for words in synonyms.values() for w in words)


async def build_documents() -> list[dict]:
    async with SessionLocal() as session:
        rows = (await session.execute(text(DOCUMENTS_SQL))).all()
    documents = []
    for r in rows:
        doc: dict[str, object] = {"id": r.id}
        for lang in LANGS:
            doc[f"title_{lang}"] = (r.titles or {}).get(lang, "")
            doc[f"body_{lang}"] = (r.bodies or {}).get(lang, "")
        names = list((r.cat_name or {}).values()) + list((r.parent_name or {}).values())
        doc["category"] = " ".join(names)
        doc["words"] = " ".join(filter(None, [words_of(r.cat_syn), words_of(r.parent_syn)]))
        doc["place"] = " ".join((r.place_names or {}).values())
        documents.append(doc)
    return documents


def postgres_search(lang: str, q: str) -> tuple[int, list[str]]:
    url = f"{API}?q={urllib.parse.quote(q)}&per_page=2&lang={lang}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return data["total"], [i["title"][:30] for i in data["items"]]


def meili_search(lang: str, q: str) -> tuple[int, list[str]]:
    res = call("POST", f"/indexes/{INDEX}/search", {"q": q, "limit": 2, "attributesToRetrieve": ["*"]})
    hits = res["hits"]
    titles = []
    for h in hits:
        title = h.get(f"title_{lang}") or next((h[f"title_{x}"] for x in LANGS if h.get(f"title_{x}")), "")
        titles.append(title[:30])
    return res.get("estimatedTotalHits", len(hits)), titles


async def main() -> None:
    documents = await build_documents()
    print(f"ads to index: {len(documents)}")

    call("DELETE", f"/indexes/{INDEX}") if _index_exists() else None
    wait_for(call("POST", "/indexes", {"uid": INDEX, "primaryKey": "id"})["taskUid"])
    wait_for(
        call(
            "PATCH",
            f"/indexes/{INDEX}/settings",
            {
                # order matters: what the seller wrote ranks above what we know about the ad
                "searchableAttributes": [
                    *(f"title_{lang}" for lang in LANGS),
                    "category",
                    "words",
                    "place",
                    *(f"body_{lang}" for lang in LANGS),
                ],
                "typoTolerance": {"enabled": True, "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8}},
            },
        )["taskUid"]
    )
    wait_for(call("POST", f"/indexes/{INDEX}/documents", documents)["taskUid"])

    stats = call("GET", f"/indexes/{INDEX}/stats")
    print(f"indexed: {stats['numberOfDocuments']} documents")
    print(f"database size on disk: {call('GET', '/stats')['databaseSize'] / 1024 / 1024:.1f} MB\n")

    print(f"{'lang':<5} {'query':<20} {'postgres':<38} meilisearch")
    print("-" * 110)
    better = worse = same = 0
    for lang, q in QUERIES:
        pg_total, pg_titles = postgres_search(lang, q)
        ms_total, ms_titles = meili_search(lang, q)
        if (pg_total == 0) != (ms_total == 0):
            mark = "  <-- meili finds it" if pg_total == 0 else "  <-- postgres finds it"
            better += pg_total == 0
            worse += ms_total == 0
        else:
            mark, same = "", same + 1
        left = f"{pg_total:<3} {' / '.join(pg_titles)}"
        right = f"{ms_total:<3} {' / '.join(ms_titles)}"
        print(f"{lang:<5} {q:<20} {left:<38} {right}{mark}")

    print(f"\nonly Meilisearch found something: {better}   only Postgres: {worse}   same verdict: {same}")
    await engine.dispose()


def _index_exists() -> bool:
    try:
        call("GET", f"/indexes/{INDEX}")
        return True
    except SystemExit:
        return False


asyncio.run(main())
