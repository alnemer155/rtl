// طبقة الاتصال بـAPI منصة المصادر — كل البيانات من الخادم، لا بيانات وهمية.

// الاتصال مباشرة بالـAPI (وليس عبر وكيل Next) — بث SSE عبر وكيل التطوير يتعطل
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export interface ChatCitation {
  index: number;
  provider: string;
  provider_label: string;
  title: string;
  detail: string;
  url: string;
  text: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  updated_at: string | null;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
  created_at: string | null;
}

export interface ConversationDetail {
  id: string;
  title: string;
  messages: ConversationMessage[];
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
  conversations: () => request<ConversationSummary[]>("/api/chat/conversations"),
  conversation: (id: number | string) => request<ConversationDetail>(`/api/chat/conversations/${id}`),
  deleteConversation: (id: string) =>
    request<{ deleted: number }>(`/api/chat/conversations/${id}`, { method: "DELETE" }),
};

/** بث محادثة عبر XHR — يعمل مع وكيل التطوير والإنتاج دون تعليق. */
export function streamChat(
  body: {
    message: string;
    conversation_id?: string;
    research_mode?: string;
    madhhab?: string;
    scholar?: string;
    book?: number;
  },
  handlers: {
    onMeta?: (payload: { conversation_id: string; route: string }) => void;
    onStatus?: (payload: { line: string }) => void;
    onSources?: (payload: { citations: ChatCitation[] }) => void;
    onDelta?: (payload: { text: string }) => void;
    onError?: (payload: { message: string }) => void;
    onDone?: (payload: { finish: string; conversation_id: string }) => void;
    onAbort?: () => void;
  },
): { abort: () => void } {
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `${API_URL}/api/chat`);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.send(JSON.stringify(body));

  let offset = 0;
  let currentEvent = "";

  const processBuffer = () => {
    const text = xhr.responseText;
    if (text.length <= offset) return;
    const fresh = text.slice(offset);
    offset = text.length;
    let buffer = fresh;
    let separator = buffer.indexOf("\n\n");
    while (separator >= 0) {
      const rawEvent = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);
      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event:")) currentEvent = line.slice(6).trim();
        else if (line.startsWith("data:")) {
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (currentEvent === "meta") handlers.onMeta?.(payload);
            else if (currentEvent === "status") handlers.onStatus?.(payload);
            else if (currentEvent === "sources") handlers.onSources?.(payload);
            else if (currentEvent === "delta") handlers.onDelta?.(payload);
            else if (currentEvent === "error") handlers.onError?.(payload);
            else if (currentEvent === "done") handlers.onDone?.(payload);
          } catch {
            // أحداث غير مكتملة تُتجاهل
          }
        }
      }
      separator = buffer.indexOf("\n\n");
    }
  };

  xhr.onreadystatechange = () => {
    if (xhr.readyState >= 3) processBuffer();
  };
  xhr.onprogress = () => processBuffer();
  xhr.onload = () => {
    processBuffer();
  };
  xhr.onabort = () => handlers.onAbort?.();
  xhr.onerror = () => handlers.onError?.({ message: "تعذر الاتصال بالخادم." });

  return { abort: () => xhr.abort() };
}
