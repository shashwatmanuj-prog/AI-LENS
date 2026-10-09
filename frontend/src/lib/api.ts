import type { Analysis, AnalysisSummary, Health, Lang } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError(0, `Can't reach the CommunityLens server at ${API_URL}. Check that the backend is running.`);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/api/health"),

  analyze: (input: { file: File; language: Lang; officialUrl?: string; community?: string }) => {
    const form = new FormData();
    form.append("file", input.file);
    form.append("language", input.language);
    if (input.officialUrl?.trim()) form.append("official_url", input.officialUrl.trim());
    if (input.community?.trim()) form.append("community", input.community.trim());
    return request<Analysis>("/api/analyze", { method: "POST", body: form });
  },

  get: (id: string) => request<Analysis>(`/api/analyses/${encodeURIComponent(id)}`),
  shared: (slug: string) => request<Analysis>(`/api/shared/${encodeURIComponent(slug)}`),
  translate: (id: string, language: Lang) =>
    request<Analysis>(`/api/analyses/${encodeURIComponent(id)}/translate`, json({ language })),
  share: (id: string, community?: string) =>
    request<{ share_slug: string; share_url: string; community: string | null }>(
      `/api/analyses/${encodeURIComponent(id)}/share`,
      json({ community: community?.trim() || null }),
    ),
  summaries: (ids: string[]) => request<AnalysisSummary[]>("/api/analyses/summaries", json({ ids })),
  community: (name: string) => request<AnalysisSummary[]>(`/api/communities/${encodeURIComponent(name)}`),
};
