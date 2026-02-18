export interface VaultStatus {
  initialized: boolean;
  locked: boolean;
}

export interface VaultSetupResponse {
  vault_path: string;
  recovery_key: string;
  message: string;
}

export interface VaultUnlockResponse {
  token: string;
  expires_in_seconds: number;
}

export interface Job {
  id: string;
  title: string;
  organisation: string | null;
  url: string | null;
  location: string | null;
  salary_range: string | null;
  deadline_type: string;
  deadline_date: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  capture_count: number;
  event_count: number;
  document_count: number;
  tags: string[];
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
}

export interface Capture {
  id: string;
  job_id: string;
  url: string | null;
  page_title: string | null;
  text_snapshot: string | null;
  html_path: string | null;
  pdf_path: string | null;
  capture_method: string;
  captured_at: string;
}

export interface AppEvent {
  id: string;
  job_id: string;
  event_type: string;
  notes: string | null;
  next_action_date: string | null;
  occurred_at: string;
}

export interface Document {
  id: string;
  job_id: string;
  doc_type: string;
  original_filename: string;
  stored_path: string;
  file_hash: string;
  file_size_bytes: number;
  version_label: string | null;
  mime_type: string | null;
  created_at: string;
  submitted_at: string | null;
}

export interface MatchResult {
  score: number;
  matched: string[];
  missing: string[];
  job_keyword_count: number;
  doc_keyword_count: number;
}

export interface Tag {
  id: string;
  name: string;
  color: string | null;
  job_count: number;
}

export interface SearchResult {
  job_id: string;
  job_title: string;
  organisation: string | null;
  source: string;
  snippet: string;
  rank: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export type EventType =
  | 'SAVED' | 'SHORTLISTED' | 'DRAFTING' | 'SUBMITTED'
  | 'INTERVIEW' | 'OFFER' | 'REJECTED' | 'WITHDRAWN' | 'EXPIRED';

export type DocType =
  | 'cv' | 'cover_letter' | 'research_statement'
  | 'teaching_statement' | 'transcript' | 'portfolio' | 'other';

export interface Analytics {
  total_jobs: number;
  by_status: Record<string, number>;
  submitted_count: number;
  response_rate: number | null;
  interview_rate: number | null;
  offer_rate: number | null;
  ghost_count: number;
  ghost_rate: number | null;
  avg_days_to_interview: number | null;
  avg_days_to_decision: number | null;
  top_orgs: Array<{
    name: string;
    total: number;
    responded: number;
    interviews: number;
    offers: number;
  }>;
}
