export const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "请求失败");
  }
  return response.json();
}

export type Reference = { title: string; content: string };
export type ReplyResponse = {
  answer: string;
  category: string;
  confidence: number;
  need_human_review: boolean;
  references: Reference[];
};

export type KnowledgeFile = {
  id: number;
  filename: string;
  category: string;
  upload_time: string;
  parsed_text: string;
  chunk_count: number;
  status: string;
};

export type FAQItem = {
  id: number;
  question: string;
  answer: string;
  category: string;
  allow_auto_reply: boolean;
  created_at: string;
  updated_at: string;
};

export type HistoryItem = {
  id: number;
  student_question: string;
  ai_answer: string;
  final_answer: string;
  category: string;
  confidence: number;
  need_human_review: boolean;
  created_at: string;
};

export type AIProviderConfig = {
  id: string;
  label: string;
  provider_type: string;
  base_url: string;
  model: string;
  api_key_configured: boolean;
  requires_api_key: boolean;
  docs_url?: string | null;
  note?: string | null;
};

export type AISettings = {
  ai_provider: string;
  providers: AIProviderConfig[];
};

export type AIProviderConfigUpdate = {
  id: string;
  api_key?: string;
  base_url?: string;
  model?: string;
};

export type AISettingsUpdate = {
  ai_provider: string;
  providers: AIProviderConfigUpdate[];
};

export type AIModelListResponse = {
  models: string[];
  source: string;
};

export const api = {
  generateReply: (question: string, style = "normal") =>
    request<ReplyResponse>("/api/reply/generate", {
      method: "POST",
      body: JSON.stringify({ question, style })
    }),
  rewriteReply: (question: string, answer: string, style: string) =>
    request<{ answer: string }>("/api/reply/rewrite", {
      method: "POST",
      body: JSON.stringify({ question, answer, style })
    }),
  uploadKnowledge: (formData: FormData) =>
    request<KnowledgeFile>("/api/knowledge/upload", { method: "POST", body: formData }),
  listKnowledge: () => request<KnowledgeFile[]>("/api/knowledge/list"),
  deleteKnowledge: (id: number) => request(`/api/knowledge/${id}`, { method: "DELETE" }),
  reindexKnowledge: (id: number) => request<KnowledgeFile>(`/api/knowledge/${id}/reindex`, { method: "POST" }),
  createFAQ: (payload: Partial<FAQItem>) =>
    request<FAQItem>("/api/faq/create", { method: "POST", body: JSON.stringify(payload) }),
  listFAQ: (keyword = "") => request<FAQItem[]>(`/api/faq/list${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`),
  updateFAQ: (id: number, payload: Partial<FAQItem>) =>
    request<FAQItem>(`/api/faq/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteFAQ: (id: number) => request(`/api/faq/${id}`, { method: "DELETE" }),
  listHistory: (keyword = "", category = "") => {
    const params = new URLSearchParams();
    if (keyword) params.set("keyword", keyword);
    if (category) params.set("category", category);
    return request<HistoryItem[]>(`/api/history/list${params.toString() ? `?${params}` : ""}`);
  },
  createHistory: (payload: Partial<HistoryItem>) =>
    request<HistoryItem>("/api/history/create", { method: "POST", body: JSON.stringify(payload) }),
  getAISettings: () => request<AISettings>("/api/settings/ai"),
  updateAISettings: (payload: AISettingsUpdate) =>
    request<AISettings>("/api/settings/ai", { method: "PUT", body: JSON.stringify(payload) }),
  listAIModels: (payload: { provider_id: string; api_key?: string; base_url?: string }) =>
    request<AIModelListResponse>("/api/settings/ai/models", { method: "POST", body: JSON.stringify(payload) })
};
