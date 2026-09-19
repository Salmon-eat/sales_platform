"""Search layer (spec §5, §7).

params.py         URL query -> Filters + canonical query (301 target)
understanding.py  "водій се мадрид" -> profession + city + rest of the text
backend.py        SearchBackend protocol + data classes (swap Postgres for Meilisearch later)
postgres.py       PostgresSearchBackend: FTS + trigram + PostGIS + disjunctive facets
suggest.py        autocomplete
"""
