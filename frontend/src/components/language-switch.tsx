"use client";

import { LANGUAGES } from "@/lib/i18n";
import type { Lang } from "@/lib/types";
import { cn } from "@/lib/utils";

export function LanguageSwitch({
  value,
  onChange,
  label,
  disabled,
  className,
}: {
  value: Lang;
  onChange: (lang: Lang) => void;
  label: string;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className={cn("inline-flex rounded-md border bg-card p-0.5", className)}>
      {LANGUAGES.map((l) => (
        <button
          key={l.code}
          type="button"
          role="radio"
          aria-checked={value === l.code}
          lang={l.code}
          disabled={disabled}
          onClick={() => onChange(l.code)}
          className={cn(
            "rounded-[5px] px-3 py-1.5 text-sm font-semibold transition-colors disabled:opacity-50",
            value === l.code ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
