import type { Lang } from "./types";

const LOCALE: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", kn: "kn-IN" };

/** Whole calendar days from `today` to an ISO date (YYYY-MM-DD). Negative = past. */
export function daysUntil(iso: string, today: Date = new Date()): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const target = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const now = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((target - now) / 86_400_000);
}

export type Urgency = "past" | "today" | "soon" | "later";

export function urgency(days: number | null): Urgency {
  if (days === null || days > 7) return "later";
  if (days < 0) return "past";
  if (days === 0) return "today";
  return "soon";
}

export function dateParts(iso: string, lang: Lang): { day: string; month: string; year: string } | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return null;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat(LOCALE[lang], { ...o, timeZone: "UTC" }).format(d);
  return { day: String(Number(m[3])), month: fmt({ month: "short" }), year: m[1] };
}

export function formatDate(iso: string, lang: Lang): string {
  const p = dateParts(iso, lang);
  return p ? `${p.day} ${p.month} ${p.year}` : iso;
}

/** Earliest deadline that has not passed, falling back to the latest past one. */
export function nextDeadline<T extends { date: string | null }>(items: T[], today = new Date()): T | null {
  const dated = items.filter((d) => d.date && daysUntil(d.date, today) !== null);
  const upcoming = dated.filter((d) => (daysUntil(d.date!, today) ?? -1) >= 0).sort((a, b) => a.date!.localeCompare(b.date!));
  if (upcoming.length) return upcoming[0];
  return dated.sort((a, b) => b.date!.localeCompare(a.date!))[0] ?? null;
}
