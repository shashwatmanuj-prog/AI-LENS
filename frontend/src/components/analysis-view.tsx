"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ExternalLink, Globe, Loader2, Mail, MapPin, Phone } from "lucide-react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/dates";
import type { MessageKey } from "@/lib/i18n";
import type { Analysis, Extraction, Lang, VerificationStatus } from "@/lib/types";
import { readChecklist, writeChecklist } from "@/lib/saved";
import { cn } from "@/lib/utils";
import { useLang } from "./language-provider";
import { LanguageSwitch } from "./language-switch";
import { VerificationStamp } from "./verification-stamp";
import { DeadlineList } from "./deadline-list";
import { StatusBadge } from "./status-badge";
import { SharePanel } from "./share-panel";
import { Checkbox } from "./ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

export function AnalysisView({ initial, readOnly = false }: { initial: Analysis; readOnly?: boolean }) {
  const { t } = useLang();
  const [analysis, setAnalysis] = useState(initial);
  const [resultLang, setResultLang] = useState<Lang>(initial.language);
  const [translating, setTranslating] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);

  const ex: Extraction =
    resultLang === analysis.language ? analysis.extraction : analysis.translations[resultLang] ?? analysis.extraction;

  async function changeLang(next: Lang) {
    setTranslateError(null);
    setResultLang(next);
    if (next === analysis.language || analysis.translations[next]) return;
    setTranslating(true);
    try {
      setAnalysis(await api.translate(analysis.id, next));
    } catch (err) {
      setTranslateError(err instanceof Error ? err.message : String(err));
      setResultLang(analysis.language);
    } finally {
      setTranslating(false);
    }
  }

  const statusById = useMemo(() => {
    const map: Record<string, VerificationStatus> = {};
    for (const c of analysis.verification.claims) map[c.claim_id] = c.status;
    return map;
  }, [analysis.verification.claims]);

  const labelById = useMemo(() => {
    const map: Record<string, string> = {};
    for (const d of ex.deadlines) map[d.id] = d.label;
    for (const f of ex.key_facts) map[f.id] = f.label;
    return map;
  }, [ex]);

  return (
    <article lang={resultLang}>
      <header className="flex flex-col gap-4 border-b pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">
            {ex.issuing_authority ?? analysis.file_name}
          </p>
          <h1 className="mt-1 max-w-[30ch] text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">{ex.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t("read_by", { model: analysis.model })}. {t("pages", { n: analysis.pages_analyzed })}.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <LanguageSwitch value={resultLang} onChange={changeLang} label={t("output_language")} disabled={translating} />
          {translating && (
            <span className="flex items-center gap-1.5 text-sm text-muted-foreground" role="status">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {t("translating")}
            </span>
          )}
        </div>
      </header>
      {translateError && (
        <p role="alert" className="mt-3 text-sm text-seal">
          {translateError}
        </p>
      )}

      <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        <div className="grid min-w-0 content-start gap-10">
          <section aria-labelledby="summary-h">
            <h2 id="summary-h" className="text-xl font-bold">
              {t("summary")}
            </h2>
            <p className="measure mt-2 text-[1.05rem]">{ex.summary}</p>
          </section>

          {ex.warnings.length > 0 && (
            <section aria-labelledby="warn-h" className="rounded-lg border-l-4 border-marigold bg-marigold-soft p-4">
              <h2 id="warn-h" className="flex items-center gap-2 font-bold">
                <AlertTriangle className="h-4 w-4" aria-hidden /> {t("warnings")}
              </h2>
              <ul className="mt-2 grid list-disc gap-1 pl-5 text-sm">
                {ex.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="deadlines-h">
            <h2 id="deadlines-h" className="text-xl font-bold">
              {t("deadlines")}
            </h2>
            <DeadlineList deadlines={ex.deadlines} statusById={statusById} lang={resultLang} />
          </section>

          <Checklist analysisId={analysis.id} items={ex.checklist} lang={resultLang} />

          <section>
            <Tabs defaultValue="eligibility">
              <TabsList>
                <TabsTrigger value="eligibility">{t("eligibility")}</TabsTrigger>
                <TabsTrigger value="documents">{t("documents")}</TabsTrigger>
                <TabsTrigger value="instructions">{t("instructions")}</TabsTrigger>
                <TabsTrigger value="facts">{t("facts")}</TabsTrigger>
              </TabsList>
              <TabsContent value="eligibility">
                <PlainList items={ex.eligibility} />
              </TabsContent>
              <TabsContent value="documents">
                <PlainList items={ex.required_documents} />
              </TabsContent>
              <TabsContent value="instructions">
                <ol className="measure grid list-decimal gap-2 pl-5">
                  {ex.instructions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
                {ex.instructions.length === 0 && <Empty />}
              </TabsContent>
              <TabsContent value="facts">
                <dl className="grid gap-4">
                  {ex.key_facts.map((f) => (
                    <div key={f.id} className="grid gap-1 border-b pb-4 last:border-0">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <dt className="font-semibold">{f.label}</dt>
                        {statusById[f.id] && <StatusBadge status={statusById[f.id]} />}
                      </div>
                      <dd>{f.value}</dd>
                      {f.source_text && (
                        <dd className="border-l-2 pl-3 text-sm text-muted-foreground">
                          <q>{f.source_text}</q>
                        </dd>
                      )}
                    </div>
                  ))}
                </dl>
                {ex.key_facts.length === 0 && <Empty />}
              </TabsContent>
            </Tabs>
          </section>
        </div>

        <aside className="grid min-w-0 content-start gap-8">
          <TrustPanel analysis={analysis} labelById={labelById} />
          <LinksAndContacts ex={ex} />
          {!readOnly && <SharePanel analysis={analysis} onShared={setAnalysis} />}
        </aside>
      </div>
    </article>
  );
}

function PlainList({ items }: { items: string[] }) {
  if (items.length === 0) return <Empty />;
  return (
    <ul className="measure grid list-disc gap-2 pl-5">
      {items.map((s, i) => (
        <li key={i}>{s}</li>
      ))}
    </ul>
  );
}

function Empty() {
  return <p className="text-sm text-muted-foreground">—</p>;
}

function Checklist({ analysisId, items, lang }: { analysisId: string; items: Extraction["checklist"]; lang: Lang }) {
  const { t } = useLang();
  const [done, setDone] = useState<string[]>([]);
  useEffect(() => setDone(readChecklist(analysisId)), [analysisId]);

  function toggle(id: string, checked: boolean) {
    const next = checked ? [...new Set([...done, id])] : done.filter((x) => x !== id);
    setDone(next);
    writeChecklist(analysisId, next);
  }

  if (items.length === 0) return null;
  const count = items.filter((i) => done.includes(i.id)).length;
  return (
    <section aria-labelledby="checklist-h">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="checklist-h" className="text-xl font-bold">
          {t("checklist")}
        </h2>
        <span className="text-sm text-muted-foreground" aria-live="polite">
          {t("checklist_done", { done: count, total: items.length })}
        </span>
      </div>
      <ol className="mt-3 grid gap-px overflow-hidden rounded-lg border bg-border">
        {items.map((item, idx) => {
          const checked = done.includes(item.id);
          return (
            <li key={item.id} className="flex gap-3 bg-card p-4">
              <Checkbox
                id={`chk-${item.id}`}
                checked={checked}
                onCheckedChange={(v) => toggle(item.id, v === true)}
                className="mt-0.5"
              />
              <label htmlFor={`chk-${item.id}`} className="grid min-w-0 flex-1 cursor-pointer gap-0.5">
                <span className={cn("font-semibold", checked && "text-muted-foreground line-through")}>
                  <span className="mr-1.5 tabular-nums text-muted-foreground">{idx + 1}.</span>
                  {item.step}
                </span>
                {item.detail && <span className="text-sm text-muted-foreground">{item.detail}</span>}
                {item.due_date && <DueChip iso={item.due_date} lang={lang} />}
              </label>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function DueChip({ iso, lang }: { iso: string; lang: Lang }) {
  return <span className="mt-1 w-fit rounded bg-marigold-soft px-1.5 text-xs font-semibold">{formatDate(iso, lang)}</span>;
}

function TrustPanel({ analysis, labelById }: { analysis: Analysis; labelById: Record<string, string> }) {
  const { t } = useLang();
  const v = analysis.verification;
  const checkedOn = new Date(v.checked_at).toISOString().slice(0, 10);
  const checkable = v.claims.filter((c) => c.status !== "not_checkable");
  return (
    <section aria-labelledby="trust-h" className="rounded-xl border bg-card p-5">
      <h2 id="trust-h" className="text-xl font-bold">
        {t("verification")}
      </h2>
      <div className="mt-3 flex items-center gap-4">
        <VerificationStamp
          status={v.overall}
          word={t(`stamp_${v.overall}` as MessageKey)}
          ring={`OFFICIAL SOURCE CHECK ${checkedOn}`}
          className="h-32 w-32 shrink-0"
        />
        <p className="text-sm">{t(`overall_${v.overall}` as MessageKey)}</p>
      </div>

      {checkable.length > 0 && (
        <ul className="mt-5 grid gap-4">
          {checkable.map((c) => (
            <li key={c.claim_id} className="grid gap-1.5 border-t pt-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{labelById[c.claim_id] ?? c.claim_label}</span>
                <StatusBadge status={c.status} />
              </div>
              {c.evidence && (
                <blockquote className="border-l-2 border-ink/40 pl-3 text-sm text-muted-foreground">{c.evidence}</blockquote>
              )}
              {c.source_url && (
                <a
                  href={c.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex w-fit max-w-full items-center gap-1 truncate text-sm font-semibold text-primary underline-offset-4 hover:underline"
                >
                  {t("found_on")}: {hostOf(c.source_url)} <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden />
                </a>
              )}
              {c.missing_terms.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {t("missing")}: {c.missing_terms.join(", ")}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {v.sources.length > 0 && (
        <div className="mt-5 border-t pt-4">
          <h3 className="text-sm font-bold">{t("sources_checked")}</h3>
          <ul className="mt-2 grid gap-2 text-sm">
            {v.sources.map((s, i) => (
              <li key={i} className="grid gap-0.5">
                <span className="flex items-center gap-2">
                  <span
                    className={cn(
                      "h-2 w-2 shrink-0 rounded-full",
                      s.fetched ? "bg-ink" : s.official ? "bg-seal" : "bg-muted-foreground/50",
                    )}
                    aria-hidden
                  />
                  <span className="truncate">{hostOf(s.url)}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {s.fetched ? t("source_ok") : s.official ? t("source_failed") : t("source_skipped")}
                  </span>
                </span>
                {s.reason && <span className="pl-4 text-xs text-muted-foreground">{s.reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-semibold text-primary">{t("how_checked")}</summary>
        <p className="mt-2 text-muted-foreground">{v.method}</p>
      </details>
    </section>
  );
}

function LinksAndContacts({ ex }: { ex: Extraction }) {
  const { t } = useLang();
  if (ex.official_links.length === 0 && ex.contacts.length === 0) return null;
  const icon = { phone: Phone, email: Mail, website: Globe, address: MapPin, other: Globe } as const;
  return (
    <section className="grid gap-5">
      {ex.official_links.length > 0 && (
        <div>
          <h2 className="font-bold">{t("links")}</h2>
          <ul className="mt-2 grid gap-1.5 text-sm">
            {ex.official_links.map((l) => (
              <li key={l} className="break-all">
                {safeHref(l) ? (
                  <a href={safeHref(l)!} target="_blank" rel="noopener noreferrer nofollow" className="text-primary underline-offset-4 hover:underline">
                    {l}
                  </a>
                ) : (
                  l
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {ex.contacts.length > 0 && (
        <div>
          <h2 className="font-bold">{t("contacts")}</h2>
          <ul className="mt-2 grid gap-2 text-sm">
            {ex.contacts.map((c, i) => {
              const Icon = icon[c.type] ?? Globe;
              return (
                <li key={i} className="flex items-start gap-2">
                  <Icon className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="break-words">{c.value}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}

function hostOf(url: string) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/** Links printed on an uploaded notice are untrusted: only allow http(s). */
function safeHref(raw: string): string | null {
  try {
    const u = new URL(/^https?:\/\//i.test(raw) ? raw : `https://${raw}`);
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null;
  } catch {
    return null;
  }
}
