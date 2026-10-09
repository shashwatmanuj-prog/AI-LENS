"use client";

import { useState } from "react";
import { Check, Copy, Loader2, Share2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Analysis } from "@/lib/types";
import { useLang } from "./language-provider";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

export function SharePanel({ analysis, onShared }: { analysis: Analysis; onShared: (a: Analysis) => void }) {
  const { t } = useLang();
  const [community, setCommunity] = useState(analysis.community ?? "");
  const [url, setUrl] = useState<string | null>(
    analysis.is_public && analysis.share_slug && typeof window !== "undefined"
      ? `${window.location.origin}/s/${analysis.share_slug}`
      : null,
  );
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.share(analysis.id, community);
      // Prefer the current origin so links work on whatever domain the app is deployed to.
      setUrl(`${window.location.origin}/s/${res.share_slug}`);
      onShared({ ...analysis, is_public: true, share_slug: res.share_slug, community: res.community });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked; the link is still visible to copy manually */
    }
  }

  const waText = encodeURIComponent(`${analysis.extraction.title}\n${url ?? ""}`);

  return (
    <section aria-labelledby="share-h" className="rounded-xl border bg-card p-5">
      <h2 id="share-h" className="flex items-center gap-2 text-lg font-bold">
        <Share2 className="h-4 w-4" aria-hidden /> {t("share")}
      </h2>
      {!url ? (
        <div className="mt-3 grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="share-community">{t("share_with_community")}</Label>
            <Input
              id="share-community"
              value={community}
              maxLength={60}
              placeholder={t("community_hint")}
              onChange={(e) => setCommunity(e.target.value)}
            />
          </div>
          <Button onClick={create} disabled={busy}>
            {busy && <Loader2 className="animate-spin" aria-hidden />}
            {t("share_create")}
          </Button>
        </div>
      ) : (
        <div className="mt-3 grid gap-3">
          <Input readOnly value={url} aria-label={t("share")} onFocus={(e) => e.currentTarget.select()} />
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={copy}>
              {copied ? <Check aria-hidden /> : <Copy aria-hidden />}
              {copied ? t("copied") : t("copy_link")}
            </Button>
            <Button asChild variant="outline">
              <a href={`https://wa.me/?text=${waText}`} target="_blank" rel="noopener noreferrer">
                {t("whatsapp")}
              </a>
            </Button>
          </div>
          {analysis.community && (
            <a href={`/community/${encodeURIComponent(analysis.community)}`} className="text-sm font-semibold text-primary underline-offset-4 hover:underline">
              {t("community_title", { name: analysis.community })}
            </a>
          )}
        </div>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-seal">
          {error}
        </p>
      )}
    </section>
  );
}
