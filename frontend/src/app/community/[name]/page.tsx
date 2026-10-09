"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useLang } from "@/components/language-provider";
import { SummaryList } from "@/components/summary-list";
import { api } from "@/lib/api";
import type { AnalysisSummary } from "@/lib/types";

export default function CommunityFeed() {
  const { name } = useParams<{ name: string }>();
  const community = safeDecode(name);
  const { t } = useLang();
  const [items, setItems] = useState<AnalysisSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.community(community).then(setItems).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [community]);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-extrabold tracking-tight">{t("community_title", { name: community })}</h1>
      <div className="mt-6">
        {error ? (
          <p role="alert" className="text-seal">{error}</p>
        ) : items === null ? (
          <p className="flex items-center gap-2 text-muted-foreground" role="status">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("loading")}
          </p>
        ) : items.length === 0 ? (
          <p className="text-muted-foreground">{t("community_empty")}</p>
        ) : (
          <SummaryList items={items} linkTo={(s) => `/s/${s.share_slug}`} />
        )}
      </div>
    </div>
  );
}

function safeDecode(v: string) {
  try {
    return decodeURIComponent(v);
  } catch {
    return v;
  }
}
