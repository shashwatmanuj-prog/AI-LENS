"use client";

import { useParams } from "next/navigation";
import { AnalysisLoader } from "@/components/analysis-loader";
import { api } from "@/lib/api";

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  return <AnalysisLoader key={id} load={() => api.get(id)} />;
}
