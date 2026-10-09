"use client";

import { CircleCheck, CircleDashed, CircleHelp, CircleMinus, CircleX } from "lucide-react";
import type { VerificationStatus } from "@/lib/types";
import type { MessageKey } from "@/lib/i18n";
import { useLang } from "./language-provider";
import { Badge } from "./ui/badge";

const MAP = {
  verified: { variant: "verified", Icon: CircleCheck },
  partial: { variant: "partial", Icon: CircleDashed },
  not_found_on_source: { variant: "negative", Icon: CircleX },
  unverified: { variant: "neutral", Icon: CircleHelp },
  not_checkable: { variant: "neutral", Icon: CircleMinus },
} as const;

export function StatusBadge({ status }: { status: VerificationStatus }) {
  const { t } = useLang();
  const { variant, Icon } = MAP[status];
  return (
    <Badge variant={variant}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {t(`status_${status}` as MessageKey)}
    </Badge>
  );
}
