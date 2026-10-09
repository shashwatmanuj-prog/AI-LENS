"use client";

import { UploadPanel } from "@/components/upload-panel";
import { useLang } from "@/components/language-provider";
import { VerificationStamp } from "@/components/verification-stamp";

export default function HomePage() {
  const { t, lang } = useLang();
  return (
    <div className="grid items-start gap-10 lg:grid-cols-[1.05fr_1fr] lg:gap-14">
      <section className="pt-2 lg:pt-8">
        <h1 className="max-w-[16ch] text-[2.4rem] font-extrabold leading-[1.08] tracking-tight text-foreground sm:text-[3.25rem]">
          {t("hero_title")}
        </h1>
        <p className="measure mt-5 text-lg text-muted-foreground">{t("hero_body")}</p>

        <SampleNotice stampWord={t("stamp_verified")} lang={lang} />
      </section>

      <section aria-label={t("analyze")}>
        <UploadPanel />
      </section>
    </div>
  );
}

/** A miniature circular with the stamp landing on it: the product in one picture. */
function SampleNotice({ stampWord, lang }: { stampWord: string; lang: string }) {
  return (
    <figure className="relative mt-10 hidden max-w-md sm:block" aria-hidden="true">
      <div className="rotate-[-1.5deg] rounded-sm border bg-card p-5 shadow-[0_18px_40px_-24px_hsl(var(--ink)/0.45)]">
        <div className="flex items-center gap-3 border-b pb-3">
          <div className="h-9 w-9 rounded-full border-2 border-ink/50" />
          <div className="grid gap-1.5">
            <div className="h-2.5 w-44 rounded bg-foreground/70" />
            <div className="h-2 w-28 rounded bg-muted-foreground/40" />
          </div>
        </div>
        <div className="mt-4 grid gap-2">
          <div className="h-2 w-full rounded bg-muted-foreground/25" />
          <div className="h-2 w-11/12 rounded bg-muted-foreground/25" />
          <div className="h-2 w-4/5 rounded bg-muted-foreground/25" />
          <div className="mt-2 flex items-center gap-2">
            <span className="rounded bg-marigold-soft px-2 py-0.5 text-sm font-bold text-foreground">
              {lang === "hi" ? "अंतिम तिथि 15-10-2026" : lang === "kn" ? "ಕೊನೆಯ ದಿನಾಂಕ 15-10-2026" : "Last date 15-10-2026"}
            </span>
          </div>
          <div className="h-2 w-10/12 rounded bg-muted-foreground/25" />
          <div className="h-2 w-2/3 rounded bg-muted-foreground/25" />
        </div>
      </div>
      <VerificationStamp
        status="verified"
        word={stampWord}
        ring="OFFICIAL SOURCE CHECKED"
        className="absolute -bottom-8 -right-6 h-36 w-36 opacity-90 [animation-delay:350ms]"
      />
    </figure>
  );
}
