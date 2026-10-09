// Mirrors backend/app/schemas.py. Keep in sync.

export type Lang = "en" | "hi" | "kn";

export type VerificationStatus =
  | "verified"
  | "partial"
  | "not_found_on_source"
  | "unverified"
  | "not_checkable";

export interface KeyFact {
  id: string;
  label: string;
  value: string;
  source_text: string;
  category: "deadline" | "eligibility" | "fee" | "requirement" | "contact" | "location" | "other";
  confidence: "high" | "medium" | "low";
}

export interface Deadline {
  id: string;
  label: string;
  date: string | null;
  time: string | null;
  source_text: string;
}

export interface ChecklistItem {
  id: string;
  step: string;
  detail: string;
  due_date: string | null;
}

export interface Contact {
  type: "phone" | "email" | "website" | "address" | "other";
  value: string;
}

export interface Extraction {
  document_type: string;
  title: string;
  issuing_authority: string | null;
  summary: string;
  language_detected: string | null;
  key_facts: KeyFact[];
  deadlines: Deadline[];
  eligibility: string[];
  required_documents: string[];
  instructions: string[];
  checklist: ChecklistItem[];
  official_links: string[];
  contacts: Contact[];
  warnings: string[];
}

export interface ClaimVerification {
  claim_id: string;
  claim_label: string;
  status: VerificationStatus;
  source_url: string | null;
  evidence: string | null;
  matched_terms: string[];
  missing_terms: string[];
}

export interface SourceCheck {
  url: string;
  official: boolean;
  fetched: boolean;
  reason: string | null;
  title: string | null;
}

export interface VerificationReport {
  overall: VerificationStatus;
  claims: ClaimVerification[];
  sources: SourceCheck[];
  checked_at: string;
  method: string;
}

export interface Analysis {
  id: string;
  created_at: string;
  file_name: string;
  mime_type: string;
  file_path: string | null;
  language: Lang;
  model: string;
  pages_analyzed: number;
  extraction: Extraction;
  verification: VerificationReport;
  community: string | null;
  share_slug: string | null;
  is_public: boolean;
  translations: Partial<Record<Lang, Extraction>>;
}

export interface AnalysisSummary {
  id: string;
  created_at: string;
  title: string;
  document_type: string;
  issuing_authority: string | null;
  overall: VerificationStatus;
  next_deadline: string | null;
  share_slug: string | null;
  community: string | null;
}

export interface Health {
  status: string;
  model: string;
  gemma_configured: boolean;
  storage: "supabase" | "memory";
  languages: Record<Lang, string>;
  max_upload_mb: number;
  source_discovery: boolean;
}
