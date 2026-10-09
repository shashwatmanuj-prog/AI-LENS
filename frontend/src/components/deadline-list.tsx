"use client";

import { dateParts, daysUntil, urgency } from "@/lib/dates";
import type { Deadline, Lang, VerificationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useLang } from "./language-provider";
import { StatusBadge } from "./status-badge";

export function DeadlineList({
  deadlines,
  statusById,
  lang,
}: {
  deadlines: Deadline[];
  statusById: Record<string, VerificationStatus>;
  lang: Lang;
}) {
  const { t } = useLang();
  if (deadlines.length === 0) return <p className="mt-2 text-muted-foreground">{t("no_deadlines")}</p>;

  const sorted = [...deadlines].sort((a, b) => (a.date ?? "9999").localeCompare(b.date ?? "9999"));
  return (
    <ol className="mt-3 grid gap-3">
      {sorted.map((d) => {
        const days = d.date ? daysUntil(d.date) : null;
        const u = urgency(days);
        const parts = d.date ? dateParts(d.date, lang) : null;
        const when =
          days === null ? null : days < 0 ? t("overdue") : days === 0 ? t("today") : days === 1 ? t("one_day_left") : t("days_left", { n: days });
        return (
          <li key={d.id} className={cn("flex gap-4 rounded-lg border bg-card p-3", u === "past" && "opacity-70")}>
            {/* Tear-off calendar leaf */}
            <div
              className={cn(
                "flex w-16 shrink-0 flex-col overflow-hidden rounded-md border text-center",
                u === "today" || u === "soon" ? "border-marigold" : "border-border",
              )}
              aria-hidden={parts ? undefined : true}
            >
              <span className={cn("py-0.5 text-xs font-bold", u === "past" ? "bg-muted text-muted-foreground" : "bg-marigold text-foreground")}>
                {parts?.month ?? "—"}
              </span>
              <span className="text-2xl font-extrabold leading-tight tabular-nums">{parts?.day ?? "?"}</span>
              <span className="pb-0.5 text-[11px] text-muted-foreground tabular-nums">{parts?.year ?? ""}</span>
            </div>
            <div className="grid min-w-0 flex-1 content-center gap-1">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="font-semibold">{d.label}</span>
                {when && (
                  <span className={cn("text-sm font-bold", u === "today" || u === "soon" ? "text-seal" : "text-muted-foreground")}>
                    {when}
                  </span>
                )}
              </div>
              {d.time && <span className="text-sm text-muted-foreground">{d.time}</span>}
              {d.source_text && <q className="truncate text-sm text-muted-foreground">{d.source_text}</q>}
              {statusById[d.id] && <StatusBadge status={statusById[d.id]} />}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
