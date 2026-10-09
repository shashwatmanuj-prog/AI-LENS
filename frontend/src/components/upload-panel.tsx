"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, FileText, Loader2, Upload, Check } from "lucide-react";
import { API_URL, ApiError, api } from "@/lib/api";
import type { Analysis, Health, Lang } from "@/lib/types";
import { rememberAnalysis } from "@/lib/saved";
import { cn } from "@/lib/utils";
import { useLang } from "./language-provider";
import { LanguageSwitch } from "./language-switch";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

const ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";

type Phase = { kind: "idle" } | { kind: "uploading"; pct: number } | { kind: "working" } | { kind: "error"; message: string };

/** POST with XMLHttpRequest so upload progress is real, not simulated. */
function analyzeWithProgress(form: FormData, onProgress: (pct: number) => void, onUploaded: () => void) {
  return new Promise<Analysis>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/analyze`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.upload.onload = onUploaded;
    xhr.onerror = () => reject(new ApiError(0, `Can't reach the CommunityLens server at ${API_URL}.`));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* not JSON */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as Analysis);
      else {
        const detail = (body as { detail?: unknown } | null)?.detail;
        reject(new ApiError(xhr.status, typeof detail === "string" ? detail : `Request failed (${xhr.status}).`));
      }
    };
    xhr.send(form);
  });
}

export function UploadPanel() {
  const { lang, t } = useLang();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [outLang, setOutLang] = useState<Lang>(lang);
  const [officialUrl, setOfficialUrl] = useState("");
  const [community, setCommunity] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => setOutLang(lang), [lang]);
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);
  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  const maxMb = health?.max_upload_mb ?? 10;
  const busy = phase.kind === "uploading" || phase.kind === "working";

  function pick(f: File | undefined) {
    if (!f) return;
    if (!ACCEPT.split(",").includes(f.type)) {
      setPhase({ kind: "error", message: t("upload_types", { mb: maxMb }) });
      return;
    }
    if (f.size > maxMb * 1024 * 1024) {
      setPhase({ kind: "error", message: t("upload_types", { mb: maxMb }) });
      return;
    }
    setFile(f);
    setPreview(f.type.startsWith("image/") ? URL.createObjectURL(f) : null);
    setPhase({ kind: "idle" });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || busy) return;
    const form = new FormData();
    form.append("file", file);
    form.append("language", outLang);
    if (officialUrl.trim()) form.append("official_url", officialUrl.trim());
    if (community.trim()) form.append("community", community.trim());
    setPhase({ kind: "uploading", pct: 0 });
    try {
      const analysis = await analyzeWithProgress(
        form,
        (pct) => setPhase({ kind: "uploading", pct }),
        () => setPhase({ kind: "working" }),
      );
      rememberAnalysis(analysis.id);
      router.push(`/analysis/${analysis.id}`);
    } catch (err) {
      setPhase({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border bg-card p-4 shadow-[0_1px_0_hsl(var(--border)),0_12px_32px_-18px_hsl(var(--ink)/0.35)] sm:p-6">
      {health && !health.gemma_configured && (
        <p role="status" className="mb-4 flex gap-2 rounded-md border border-marigold/50 bg-marigold-soft p-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {t("server_not_ready")}
        </p>
      )}

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          "relative flex min-h-[180px] flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-5 text-center transition-colors",
          dragging ? "border-primary bg-accent" : "border-input",
        )}
      >
        {file ? (
          <div className="flex w-full items-center gap-4 text-left">
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={preview} alt="" className="h-24 w-20 shrink-0 rounded border object-cover" />
            ) : (
              <div className="flex h-24 w-20 shrink-0 items-center justify-center rounded border bg-muted">
                <FileText className="h-8 w-8 text-muted-foreground" aria-hidden />
              </div>
            )}
            <div className="min-w-0">
              <p className="truncate font-semibold">{file.name}</p>
              <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              <button
                type="button"
                className="mt-1 text-sm font-semibold text-primary underline-offset-4 hover:underline disabled:opacity-50"
                onClick={() => inputRef.current?.click()}
                disabled={busy}
              >
                {t("upload_change")}
              </button>
            </div>
          </div>
        ) : (
          <>
            <Upload className="h-7 w-7 text-ink" aria-hidden />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="font-semibold text-foreground underline decoration-marigold decoration-2 underline-offset-4"
            >
              {t("upload_drop")}
            </button>
            <p className="text-sm text-muted-foreground">{t("upload_types", { mb: maxMb })}</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label={t("upload_drop")}
          onChange={(e) => pick(e.target.files?.[0])}
        />
      </div>

      <div className="mt-5 grid gap-4">
        <div className="grid gap-2">
          <span className="text-sm font-semibold" id="out-lang">
            {t("output_language")}
          </span>
          <LanguageSwitch value={outLang} onChange={setOutLang} label={t("output_language")} disabled={busy} className="w-fit" />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="official-url">{t("official_url")}</Label>
          <Input
            id="official-url"
            type="url"
            inputMode="url"
            placeholder="https://scholarships.gov.in"
            value={officialUrl}
            onChange={(e) => setOfficialUrl(e.target.value)}
            disabled={busy}
            aria-describedby="official-url-hint"
          />
          <p id="official-url-hint" className="text-xs text-muted-foreground">
            {t("official_url_hint")}
          </p>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="community">{t("community")}</Label>
          <Input
            id="community"
            placeholder={t("community_hint")}
            maxLength={60}
            value={community}
            onChange={(e) => setCommunity(e.target.value)}
            disabled={busy}
          />
        </div>
      </div>

      {phase.kind === "error" && (
        <p role="alert" className="mt-4 rounded-md border border-seal/40 bg-seal/10 p-3 text-sm text-seal">
          {phase.message}
        </p>
      )}

      {busy ? (
        <ol className="mt-5 grid gap-2 text-sm" aria-live="polite">
          <ProgressRow
            done={phase.kind === "working"}
            active={phase.kind === "uploading"}
            label={phase.kind === "uploading" ? `${t("step_upload")} (${phase.pct}%)` : t("step_upload")}
          />
          <ProgressRow done={false} active={phase.kind === "working"} label={`${t("step_read")}, ${t("step_check").toLowerCase()}`} />
        </ol>
      ) : (
        <Button type="submit" size="lg" className="mt-5 w-full" disabled={!file}>
          {t("analyze")}
        </Button>
      )}
    </form>
  );
}

function ProgressRow({ done, active, label }: { done: boolean; active: boolean; label: string }) {
  return (
    <li className={cn("flex items-center gap-2", !done && !active && "text-muted-foreground")}>
      {done ? (
        <Check className="h-4 w-4 text-ink" aria-hidden />
      ) : active ? (
        <Loader2 className="h-4 w-4 animate-spin text-ink" aria-hidden />
      ) : (
        <span className="h-4 w-4 rounded-full border" aria-hidden />
      )}
      {label}
    </li>
  );
}
