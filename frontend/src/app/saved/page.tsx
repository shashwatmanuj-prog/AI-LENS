"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { useLang } from "@/components/language-provider";
import { SummaryList } from "@/components/summary-list";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { getSavedIds } from "@/lib/saved";
import type { AnalysisSummary } from "@/lib/types";

export default function SavedPage() {
  const { t } = useLang();
  const [items, setItems] = useState<AnalysisSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ids = getSavedIds();
    if (ids.length === 0) return setItems([]);
    api
      .summaries(ids)
      .then((rows) => setItems(ids.map((id) => rows.find((r) => r.id === id)).filter((r): r is AnalysisSummary => !!r)))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("saved_title")}</h1>
      <div className="mt-6">
        {error ? (
          <p role="alert" className="text-seal">{error}</p>
        ) : items === null ? (
          <p className="flex items-center gap-2 text-muted-foreground" role="status">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("loading")}
          </p>
        ) : items.length === 0 ? (
          <div className="grid gap-4">
            <p className="text-muted-foreground">{t("saved_empty")}</p>
            <Button asChild className="w-fit">
              <Link href="/">{t("nav_home")}</Link>
            </Button>
          </div>
        ) : (
          <SummaryList items={items} linkTo={(s) => `/analysis/${s.id}`} />
        )}
      </div>
    </div>
  );
}
