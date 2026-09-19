// Fails when a locale misses a key present in the Ukrainian source or has extra keys.
// Site texts: messages/<locale>.json; admin texts: messages/admin/<locale>/<namespace>.json.
// Run in CI: npm run check:messages
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const DIR = new URL("../messages/", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const LOCALES = ["uk", "es", "en", "ru"];

function keys(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === "object" ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

const load = (file) => JSON.parse(readFileSync(file, "utf8"));
let failed = false;
let total = 0;

function compare(label, files) {
  const source = new Set(keys(load(files.uk)));
  total += source.size;
  for (const locale of LOCALES.filter((l) => l !== "uk")) {
    if (!existsSync(files[locale])) {
      console.error(`${label}: missing file for ${locale}`);
      failed = true;
      continue;
    }
    const current = new Set(keys(load(files[locale])));
    for (const k of source) if (!current.has(k)) console.error(`${label} [${locale}]: missing "${k}"`), (failed = true);
    for (const k of current) if (!source.has(k)) console.error(`${label} [${locale}]: extra "${k}"`), (failed = true);
  }
}

compare("site", Object.fromEntries(LOCALES.map((l) => [l, join(DIR, `${l}.json`)])));
for (const ns of readdirSync(join(DIR, "admin", "uk")).filter((f) => f.endsWith(".json"))) {
  compare(`admin/${ns}`, Object.fromEntries(LOCALES.map((l) => [l, join(DIR, "admin", l, ns)])));
}

if (failed) process.exit(1);
console.log(`messages OK: ${total} keys in every locale (site + admin)`);
