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

async function requestBlob(path: string, options?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "请求失败");
  }
  return response.blob();
}

export type Reference = { title: string; content: string };
export type ReplyResponse = {
  answer: string;
  category: string;
  confidence: number;
  need_human_review: boolean;
  references: Reference[];
  ai_used: boolean;
  ai_provider?: string | null;
  ai_model?: string | null;
  ai_error?: string | null;
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

export type FAQImportResponse = {
  imported: number;
  skipped_duplicates: number;
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

export type AIProviderTestResponse = {
  ok: boolean;
  message: string;
  latency_ms: number;
  preview: string;
};

export type BackupImportResponse = {
  ok: boolean;
  imported_faq: number;
  skipped_faq_duplicates: number;
  imported_knowledge_files: number;
  imported_history: number;
};

export type AppInfo = {
  name: string;
  version: string;
  developer: string;
  latest_update: string;
};

export type UpdateCheckResponse = {
  current_version: string;
  latest_version: string;
  has_update: boolean;
  release_url: string;
  asset_name?: string | null;
  download_url?: string | null;
  asset_size?: number | null;
  digest?: string | null;
  published_at?: string | null;
  body: string;
  min_supported_version?: string | null;
  force_update: boolean;
  update_required_message?: string | null;
};

export type UpdateInstallResponse = {
  ok: boolean;
  message: string;
  installer_path?: string | null;
};

export type StudentLinkResponse = {
  url: string;
};

export type StudentReplyResponse = {
  answer: string;
  category: string;
  need_human_review: boolean;
};

export type UpdateProgressResponse = {
  status: "idle" | "checking" | "downloading" | "launching" | "completed" | "error";
  phase: string;
  message: string;
  bytes_downloaded: number;
  bytes_total?: number | null;
  percent: number;
  latest_version?: string | null;
  asset_name?: string | null;
  installer_path?: string | null;
  error?: string | null;
};

export type DeleteResponse = {
  ok: boolean;
  deleted: number;
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
  updateKnowledge: (id: number, payload: Partial<KnowledgeFile>) =>
    request<KnowledgeFile>(`/api/knowledge/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteKnowledge: (id: number) => request(`/api/knowledge/${id}`, { method: "DELETE" }),
  reindexKnowledge: (id: number) => request<KnowledgeFile>(`/api/knowledge/${id}/reindex`, { method: "POST" }),
  createFAQ: (payload: Partial<FAQItem> & { force?: boolean }) =>
    request<FAQItem>("/api/faq/create", { method: "POST", body: JSON.stringify(payload) }),
  listFAQ: (keyword = "") => request<FAQItem[]>(`/api/faq/list${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`),
  similarFAQ: (question: string, excludeId?: number) => {
    const params = new URLSearchParams({ question });
    if (excludeId) params.set("exclude_id", String(excludeId));
    return request<FAQItem[]>(`/api/faq/similar?${params}`);
  },
  importFAQ: (formData: FormData) =>
    request<FAQImportResponse>("/api/faq/import", { method: "POST", body: formData }),
  exportFAQ: (keyword = "") =>
    requestBlob(`/api/faq/export${keyword ? `?keyword=${encodeURIComponent(keyword)}` : ""}`),
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
  deleteHistory: (ids: number[]) =>
    request<DeleteResponse>("/api/history/delete", { method: "POST", body: JSON.stringify({ ids }) }),
  deleteHistoryItem: (id: number) => request<DeleteResponse>(`/api/history/${id}`, { method: "DELETE" }),
  getAISettings: () => request<AISettings>("/api/settings/ai"),
  updateAISettings: (payload: AISettingsUpdate) =>
    request<AISettings>("/api/settings/ai", { method: "PUT", body: JSON.stringify(payload) }),
  listAIModels: (payload: { provider_id: string; api_key?: string; base_url?: string }) =>
    request<AIModelListResponse>("/api/settings/ai/models", { method: "POST", body: JSON.stringify(payload) }),
  testAIProvider: (payload: { provider_id: string; api_key?: string; base_url?: string; model?: string }) =>
    request<AIProviderTestResponse>("/api/settings/ai/test", { method: "POST", body: JSON.stringify(payload) }),
  getAppInfo: () => request<AppInfo>("/api/app/info"),
  getStudentLink: () => request<StudentLinkResponse>("/api/app/student-link"),
  checkUpdate: () => request<UpdateCheckResponse>("/api/app/update/check"),
  installUpdate: () => request<UpdateInstallResponse>("/api/app/update/install", { method: "POST" }),
  getUpdateProgress: () => request<UpdateProgressResponse>("/api/app/update/progress"),
  generateStudentReply: (question: string, accessKey: string, style = "normal") =>
    request<StudentReplyResponse>("/api/student/reply/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Student-Access-Key": accessKey },
      body: JSON.stringify({ question, style })
    }),
  exportData: () => requestBlob("/api/data/export"),
  importData: (formData: FormData) =>
    request<BackupImportResponse>("/api/data/import", { method: "POST", body: formData })
};
