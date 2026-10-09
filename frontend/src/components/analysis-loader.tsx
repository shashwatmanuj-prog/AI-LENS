"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { ApiError } from "@/lib/api";
import type { Analysis } from "@/lib/types";
import { rememberAnalysis } from "@/lib/saved";
import { AnalysisView } from "./analysis-view";
import { useLang } from "./language-provider";
import { Button } from "./ui/button";

export function AnalysisLoader({ load, readOnly = false }: { load: () => Promise<Analysis>; readOnly?: boolean }) {
  const { t } = useLang();
  const [state, setState] = useState<{ data?: Analysis; error?: ApiError | Error }>({});
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let alive = true;
    setState({});
    load()
      .then((data) => {
        if (!alive) return;
        if (!readOnly) rememberAnalysis(data.id);
        setState({ data });
      })
      .catch((error) => alive && setState({ error }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  if (state.data) return <AnalysisView initial={state.data} readOnly={readOnly} />;
  if (state.error) {
    const notFound = state.error instanceof ApiError && state.error.status === 404;
    return (
      <div className="measure grid gap-4 py-10">
        <p role="alert" className="text-lg">
          {notFound ? t("not_found") : state.error.message}
        </p>
        <div className="flex gap-2">
          {!notFound && <Button onClick={() => setAttempt((n) => n + 1)}>{t("try_again")}</Button>}
          <Button asChild variant="outline">
            <Link href="/">{t("read_another")}</Link>
          </Button>
        </div>
      </div>
    );
  }
  return (
    <p className="flex items-center gap-2 py-10 text-muted-foreground" role="status">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> {t("loading")}
    </p>
  );
}
