"use client";

import Link from "next/link";
import { formatDate } from "@/lib/dates";
import type { AnalysisSummary } from "@/lib/types";
import { useLang } from "./language-provider";
import { StatusBadge } from "./status-badge";

export function SummaryList({ items, linkTo }: { items: AnalysisSummary[]; linkTo: (s: AnalysisSummary) => string }) {
  const { t, lang } = useLang();
  return (
    <ul className="grid divide-y overflow-hidden rounded-xl border bg-card">
      {items.map((s) => (
        <li key={s.id}>
          <Link href={linkTo(s)} className="grid gap-1 p-4 hover:bg-accent/60 focus-visible:bg-accent sm:grid-cols-[1fr_auto] sm:items-center sm:gap-4">
            <span className="min-w-0">
              <span className="block truncate font-semibold">{s.title}</span>
              <span className="block truncate text-sm text-muted-foreground">
                {s.issuing_authority ?? s.document_type}
              </span>
            </span>
            <span className="flex flex-wrap items-center gap-3 text-sm">
              {s.next_deadline && (
                <span>
                  <span className="text-muted-foreground">{t("next_deadline")}: </span>
                  <span className="font-semibold">{formatDate(s.next_deadline, lang)}</span>
                </span>
              )}
              <StatusBadge status={s.overall} />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
