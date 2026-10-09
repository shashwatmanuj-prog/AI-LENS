"use client";

import { useId } from "react";
import type { VerificationStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONE: Record<VerificationStatus, string> = {
  verified: "text-ink",
  partial: "text-marigold",
  not_found_on_source: "text-seal",
  unverified: "text-muted-foreground",
  not_checkable: "text-muted-foreground",
};

/**
 * A rubber stamp, the way an Indian office marks a document as checked.
 * Only the backend's verification status drives it; it never shows "verified"
 * unless the verifier found the values on an official page.
 */
export function VerificationStamp({
  status,
  word,
  ring,
  className,
  animate = true,
}: {
  status: VerificationStatus;
  word: string;
  ring: string;
  className?: string;
  animate?: boolean;
}) {
  const id = useId().replace(/:/g, "");
  const solid = status === "verified" || status === "not_found_on_source" || status === "partial";
  const ringText = `${ring} ★ ${ring} ★ `;
  return (
    <svg
      viewBox="0 0 200 200"
      role="img"
      aria-label={word}
      className={cn("-rotate-[8deg]", TONE[status], animate && "motion-safe:animate-stamp", className)}
    >
      <defs>
        <path id={`ring-${id}`} d="M100,100 m-72,0 a72,72 0 1,1 144,0 a72,72 0 1,1 -144,0" />
        {/* Uneven ink: a turbulence mask so the stamp doesn't look vector-perfect. */}
        <filter id={`ink-${id}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" result="noise" />
          <feColorMatrix in="noise" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.6 1.25" result="speckle" />
          <feComposite in="SourceGraphic" in2="speckle" operator="in" />
        </filter>
      </defs>
      <g filter={`url(#ink-${id})`} fill="currentColor" stroke="currentColor">
        <circle cx="100" cy="100" r="94" fill="none" strokeWidth="6" strokeDasharray={solid ? undefined : "10 7"} />
        <circle cx="100" cy="100" r="56" fill="none" strokeWidth="2.5" />
        <text fontSize="15" fontWeight="700" letterSpacing="2.5" stroke="none">
          <textPath href={`#ring-${id}`} startOffset="0">
            {ringText}
          </textPath>
        </text>
        <rect x="18" y="84" width="164" height="34" rx="3" fill="hsl(var(--card))" strokeWidth="3" />
        <text
          x="100"
          y="108"
          textAnchor="middle"
          fontSize={word.length > 12 ? 13 : word.length > 9 ? 16 : 20}
          fontWeight="800"
          letterSpacing="1.5"
          stroke="none"
        >
          {word}
        </text>
      </g>
    </svg>
  );
}
