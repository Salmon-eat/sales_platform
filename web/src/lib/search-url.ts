/** Query-string helpers for search pages. The API decides what is canonical; these only build links. */

export type Pairs = [string, string][];
export type RawSearchParams = Record<string, string | string[] | undefined>;

export function pairsFromSearchParams(sp: RawSearchParams): Pairs {
  return Object.entries(sp).flatMap(([key, value]) =>
    value === undefined ? [] : (Array.isArray(value) ? value : [value]).map((v): [string, string] => [key, v]),
  );
}

export function parsePairs(query: string): Pairs {
  if (!query) return [];
  return query.split("&").map((part) => {
    const [key, value = ""] = part.split("=");
    return [decodeURIComponent(key), decodeURIComponent(value)];
  });
}

export function get(pairs: Pairs, key: string): string | undefined {
  return pairs.find(([k]) => k === key)?.[1];
}

export function sortPairs(pairs: Pairs): Pairs {
  return [...pairs].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
}

export function toQuery(pairs: Pairs): string {
  return pairs.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v).replace(/%2C/gi, ",")}`).join("&");
}

export function samePairs(a: Pairs, b: Pairs): boolean {
  return a.length === b.length && a.every(([k, v], i) => k === b[i][0] && v === b[i][1]);
}

/** Set (or remove with null) a parameter; any change resets pagination. */
export function setParam(pairs: Pairs, key: string, value: string | null): Pairs {
  const rest = pairs.filter(([k]) => k !== key && k !== "page");
  return sortPairs(value === null || value === "" ? rest : [...rest, [key, value]]);
}

export function toggleValue(pairs: Pairs, key: string, value: string, mode: "bool" | "multi" | "single"): Pairs {
  const current = get(pairs, key);
  if (mode === "bool") return setParam(pairs, key, current ? null : "1");
  if (mode === "single") return setParam(pairs, key, current === value ? null : value);
  const values = new Set((current ?? "").split(",").filter(Boolean));
  if (values.has(value)) values.delete(value);
  else values.add(value);
  return setParam(pairs, key, [...values].sort().join(","));
}

export function isActive(pairs: Pairs, key: string, value: string, mode: "bool" | "multi" | "single"): boolean {
  const current = get(pairs, key);
  if (!current) return false;
  return mode === "multi" ? current.split(",").includes(value) : mode === "bool" || current === value;
}

export function href(path: string, pairs: Pairs): string {
  const query = toQuery(pairs);
  return query ? `${path}?${query}` : path;
}
