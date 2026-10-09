"use client";

import { useParams } from "next/navigation";
import { AnalysisLoader } from "@/components/analysis-loader";
import { api } from "@/lib/api";

export default function SharedPage() {
  const { slug } = useParams<{ slug: string }>();
  return <AnalysisLoader key={slug} load={() => api.shared(slug)} readOnly />;
}
