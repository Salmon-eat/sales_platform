"use client";

/**
 * Saved listings and sent applications, kept in this browser until sign-in exists (stage 6).
 * After sign-in they move into the account (spec §10: "перенесення обраного з localStorage в акаунт").
 */
import { useCallback, useMemo, useSyncExternalStore } from "react";

const FAVORITES = "bazarcito:favorites";
const APPLIED = "bazarcito:applied";
const EVENT = "bazarcito:saved";
const LIMIT = 100; // same as GET /v1/listings/cards

export type AppliedEntry = { id: number; at: string };

function read(key: string): string {
  try {
    return localStorage.getItem(key) ?? "[]";
  } catch {
    return "[]"; // storage blocked (private mode, disabled site data)
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage blocked: the change lives until reload */
  }
  window.dispatchEvent(new Event(EVENT));
}

function parse<T>(raw: string, fallback: T): T {
  try {
    const value = JSON.parse(raw);
    return Array.isArray(value) ? (value as T) : fallback;
  } catch {
    return fallback;
  }
}

function subscribe(onChange: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === FAVORITES || e.key === APPLIED || e.key === "bazarcito:viewed") onChange(); // other tabs
  };
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

// the server has no storage: render "nothing saved" first, then the real state after hydration
const serverSnapshot = () => "[]";

export function useFavorites() {
  const raw = useSyncExternalStore(subscribe, () => read(FAVORITES), serverSnapshot);
  const ids = useMemo(() => parse<number[]>(raw, []).filter(Number.isInteger), [raw]);
  const toggle = useCallback((id: number) => {
    const current = parse<number[]>(read(FAVORITES), []);
    write(FAVORITES, current.includes(id) ? current.filter((x) => x !== id) : [id, ...current].slice(0, LIMIT));
  }, []);
  return { ids, has: (id: number) => ids.includes(id), toggle };
}

export function useApplied() {
  const raw = useSyncExternalStore(subscribe, () => read(APPLIED), serverSnapshot);
  const entries = useMemo(() => parse<AppliedEntry[]>(raw, []).filter((e) => Number.isInteger(e?.id)), [raw]);
  return { entries, get: (id: number) => entries.find((e) => e.id === id) };
}

export function markApplied(id: number) {
  const current = parse<AppliedEntry[]>(read(APPLIED), []).filter((e) => e.id !== id);
  write(APPLIED, [{ id, at: new Date().toISOString() }, ...current].slice(0, LIMIT));
}

export function forgetApplied(id: number) {
  write(APPLIED, parse<AppliedEntry[]>(read(APPLIED), []).filter((e) => e.id !== id));
}

/** Ads opened in this browser, the latest first: their cards look "visited", like links in Google results,
 * and the home page shows them back as the visitor's history. */
const VIEWED = "bazarcito:viewed";
const VIEWED_LIMIT = 500;

export function useViewed() {
  const raw = useSyncExternalStore(subscribe, () => read(VIEWED), serverSnapshot);
  const ids = useMemo(() => new Set(parse<number[]>(raw, []).filter(Number.isInteger)), [raw]);
  return { has: (id: number) => ids.has(id) };
}

/** The opened ads in order, the latest first. */
export function useViewedIds(): number[] {
  const raw = useSyncExternalStore(subscribe, () => read(VIEWED), serverSnapshot);
  return useMemo(() => parse<number[]>(raw, []).filter(Number.isInteger), [raw]);
}

export function clearViewed() {
  write(VIEWED, []);
}

export function markViewed(id: number) {
  const current = parse<number[]>(read(VIEWED), []);
  if (current[0] === id) return;
  write(VIEWED, [id, ...current.filter((x) => x !== id)].slice(0, VIEWED_LIMIT));
}

/** The candidate's name and phone from the last application: the next one is sent in one click.
 * Kept only in this browser; "not me" forgets them (shared phone or computer). */
export type SavedContact = {
  name: string;
  phone: string;
  messenger: "phone" | "telegram" | "whatsapp" | "viber";
  in_spain: boolean | null;
};

const CONTACT = "bazarcito:contact";
const MESSENGERS = new Set(["phone", "telegram", "whatsapp", "viber"]);

function subscribeContact(onChange: () => void) {
  const onStorage = (e: StorageEvent) => {
    if (e.key === CONTACT) onChange();
  };
  window.addEventListener(EVENT, onChange);
  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener(EVENT, onChange);
    window.removeEventListener("storage", onStorage);
  };
}

function readContact(): string {
  try {
    return localStorage.getItem(CONTACT) ?? "";
  } catch {
    return "";
  }
}

export function useSavedContact(): SavedContact | null {
  const raw = useSyncExternalStore(subscribeContact, readContact, () => "");
  return useMemo(() => {
    if (!raw) return null;
    try {
      const c = JSON.parse(raw) as Partial<SavedContact>;
      if (typeof c.name !== "string" || typeof c.phone !== "string" || !c.name || !c.phone) return null;
      return {
        name: c.name,
        phone: c.phone,
        messenger: MESSENGERS.has(c.messenger ?? "") ? (c.messenger as SavedContact["messenger"]) : "phone",
        in_spain: typeof c.in_spain === "boolean" ? c.in_spain : null,
      };
    } catch {
      return null;
    }
  }, [raw]);
}

export function saveContact(contact: SavedContact) {
  write(CONTACT, contact);
}

export function forgetContact() {
  try {
    localStorage.removeItem(CONTACT);
  } catch {
    /* storage blocked */
  }
  window.dispatchEvent(new Event(EVENT));
}
