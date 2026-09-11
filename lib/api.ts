// طبقة الاتصال بـAPI منصة المصادر — كل البيانات من الخادم، لا بيانات وهمية.

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

export interface Madhhab {
  id: number;
  key: string;
  name_ar: string;
  name_en: string;
  schools: { id: number; key: string; name_ar: string; name_en: string }[];
}

export interface Scholar {
  id: number;
  key: string;
  name_ar: string;
  name_en: string | null;
}

export interface SourceInfo {
  id: number;
  key: string;
  name: string;
  domain: string;
  base_url: string;
  source_type: string;
  official: boolean;
  language: string;
  madhhab_id: number | null;
}

export interface SectionNode {
  id: number;
  title: string;
  depth: number;
  position: number;
  source_url: string;
  issue_count: number;
  children: SectionNode[];
}

export interface BookSummary {
  id: number;
  title: string;
  scholar: string | null;
  madhhab: string | null;
  school: string | null;
  language: string;
  source_url: string;
  cover_url: string | null;
  sections_count: number;
  issues_count: number;
  edition?: string | null;
  volume?: string | null;
  toc?: SectionNode[];
}

export interface Issue {
  id: number;
  issue_number: number | null;
  title: string | null;
  text_original: string;
  book_id: number;
  book_title: string;
  scholar: string | null;
  madhhab: string | null;
  school: string | null;
  section_path: string | null;
  section_id: number;
  source_url: string;
  content_hash: string;
  source_revision: number;
  scraped_at: string | null;
  verified_at: string | null;
}

export interface SearchHit {
  issue: Issue;
  score: number;
  snippet: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  page_size: number;
  results: SearchHit[];
}

export interface Citation {
  index: number;
  issue_id: number;
  issue_number: number | null;
  scholar: string | null;
  book_title: string;
  section_path: string | null;
  madhhab: string | null;
  source_url: string;
  text_original: string;
}

export interface AskFilters {
  madhhab?: string;
  scholar?: string;
  book?: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(detail && !detail.startsWith("<") ? detail : `خطأ ${response.status} من الخادم`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; issues_count: number; ai_configured: boolean }>("/api/health"),
  madhhabs: () => request<Madhhab[]>("/api/madhhabs"),
  scholars: () => request<Scholar[]>("/api/scholars"),
  sources: () => request<SourceInfo[]>("/api/sources"),
  books: () => request<BookSummary[]>("/api/books"),
  book: (id: number | string) => request<BookSummary>(`/api/books/${id}`),
  issue: (id: number | string) => request<Issue>(`/api/issues/${id}`),
  search: (params: Record<string, string | number | undefined>) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    return request<SearchResponse>(`/api/search?${query.toString()}`);
  },
  stats: () =>
    request<{
      books: number;
      sections: number;
      issues: number;
      scholars: number;
      sources: number;
      madhhabs: number;
      crawl_runs_total: number;
      crawl_runs_failed: number;
      ai_answers: number;
      last_crawl: {
        id: number;
        status: string;
        pages_processed: number;
        records_created: number;
        records_updated: number;
        records_unchanged: number;
        records_failed: number;
        started_at: string | null;
        finished_at: string | null;
      } | null;
    }>("/api/admin/stats"),
  crawlRuns: () =>
    request<
      {
        id: number;
        status: string;
        book_id: number | null;
        pages_processed: number;
        records_created: number;
        records_failed: number;
        started_at: string | null;
        finished_at: string | null;
        errors: { url?: string; error?: string }[];
      }[]
    >("/api/admin/crawl-runs"),
};
