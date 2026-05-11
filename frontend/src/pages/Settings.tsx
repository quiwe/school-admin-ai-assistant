import { Activity, CheckCircle2, Download, ExternalLink, KeyRound, ListFilter, Save, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, AIProviderConfig, AISettingsUpdate, AppInfo } from "../api/client";
import { Button, Input, Panel, PrimaryButton, Select } from "../components/ui";

type ProviderForm = {
  api_key: string;
  base_url: string;
  model: string;
};

export default function SettingsPage() {
  const [activeProvider, setActiveProvider] = useState("openai");
  const [providers, setProviders] = useState<AIProviderConfig[]>([]);
  const [providerForms, setProviderForms] = useState<Record<string, ProviderForm>>({});
  const [modelOptions, setModelOptions] = useState<Record<string, string[]>>({});
  const [loadingModels, setLoadingModels] = useState(false);
  const [appInfo, setAppInfo] = useState<AppInfo | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [testingModel, setTestingModel] = useState(false);
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [backupInputKey, setBackupInputKey] = useState(0);
  const [backupStatus, setBackupStatus] = useState("");
  const [backupError, setBackupError] = useState("");

  useEffect(() => {
    loadSettings();
    api.getAppInfo().then(setAppInfo).catch(() => undefined);
  }, []);

  const activeProviderInfo = useMemo(
    () => providers.find((provider) => provider.id === activeProvider),
    [activeProvider, providers]
  );
  const activeForm = activeProviderInfo
    ? providerForms[activeProviderInfo.id] || {
        api_key: "",
        base_url: activeProviderInfo.base_url,
        model: activeProviderInfo.model
      }
    : { api_key: "", base_url: "", model: "" };

  async function loadSettings() {
    try {
      const data = await api.getAISettings();
      setActiveProvider(data.ai_provider);
      setProviders(data.providers);
      setStatus("");
      setProviderForms(
        Object.fromEntries(
          data.providers.map((provider) => [
            provider.id,
            { api_key: "", base_url: provider.base_url, model: provider.model }
          ])
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "读取设置失败");
    }
  }

  function updateProviderField(providerId: string, field: keyof ProviderForm, value: string) {
    setSaved(false);
    setStatus("");
    setProviderForms((current) => ({
      ...current,
      [providerId]: {
        api_key: current[providerId]?.api_key || "",
        base_url: current[providerId]?.base_url || "",
        model: current[providerId]?.model || "",
        [field]: value
      }
    }));
  }

  async function saveSettings() {
    setError("");
    setSaved(false);
    setStatus("");
    if (!activeProviderInfo) {
      setError("请先选择 Provider");
      return;
    }
    const trimmedBaseUrl = activeForm.base_url.trim();
    const trimmedModel = activeForm.model.trim();
    if (!trimmedModel) {
      setError("请先选择或填写模型名称");
      return;
    }
    setSaving(true);
    try {
      const payload: AISettingsUpdate = {
        ai_provider: activeProvider,
        providers: [
          {
            id: activeProvider,
            base_url: trimmedBaseUrl,
            model: trimmedModel,
            ...(activeForm.api_key.trim() ? { api_key: activeForm.api_key.trim() } : {})
          }
        ]
      };
      const data = await api.updateAISettings(payload);
      setActiveProvider(data.ai_provider);
      setProviders(data.providers);
      setProviderForms(
        Object.fromEntries(
          data.providers.map((provider) => [
            provider.id,
            { api_key: "", base_url: provider.base_url, model: provider.model }
          ])
        )
      );
      setStatus(`已保存：${activeProviderInfo.label} / ${trimmedModel}`);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function detectModels() {
    if (!activeProviderInfo) return;
    setError("");
    setSaved(false);
    setLoadingModels(true);
    try {
      const data = await api.listAIModels({
        provider_id: activeProviderInfo.id,
        api_key: activeForm.api_key || undefined,
        base_url: activeForm.base_url || undefined
      });
      setModelOptions((current) => ({ ...current, [activeProviderInfo.id]: data.models }));
      if (data.models.length > 0 && !data.models.includes(activeForm.model)) {
        updateProviderField(activeProviderInfo.id, "model", data.models[0]);
      }
      setStatus(`已识别到 ${data.models.length} 个模型，请选择后保存`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "模型识别失败");
    } finally {
      setLoadingModels(false);
    }
  }

  async function testModel() {
    if (!activeProviderInfo) return;
    setError("");
    setSaved(false);
    setTestingModel(true);
    try {
      const data = await api.testAIProvider({
        provider_id: activeProviderInfo.id,
        api_key: activeForm.api_key || undefined,
        base_url: activeForm.base_url || undefined,
        model: activeForm.model || undefined
      });
      setStatus(`${data.message}，耗时 ${data.latency_ms} ms${data.preview ? `：${data.preview}` : ""}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "模型测试失败");
    } finally {
      setTestingModel(false);
    }
  }

  async function exportBackup() {
    setBackupStatus("");
    setBackupError("");
    try {
      const blob = await api.exportData();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `school-admin-ai-assistant-backup-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setBackupStatus("已导出备份文件");
    } catch (err) {
      setBackupError(err instanceof Error ? err.message : "导出备份失败");
    }
  }

  async function importBackup() {
    if (!backupFile) return;
    setBackupStatus("");
    setBackupError("");
    const formData = new FormData();
    formData.append("file", backupFile);
    try {
      const result = await api.importData(formData);
      setBackupFile(null);
      setBackupInputKey((current) => current + 1);
      setBackupStatus(
        `已恢复：FAQ ${result.imported_faq} 条、知识库 ${result.imported_knowledge_files} 个、历史 ${result.imported_history} 条，跳过重复 FAQ ${result.skipped_faq_duplicates} 条`
      );
    } catch (err) {
      setBackupError(err instanceof Error ? err.message : "导入备份失败");
    }
  }

  return (
    <div className="space-y-4">
      <Panel
        title="常用大模型 API 设置"
        action={
          <div className="text-xs">
            {saved && <span className="text-emerald-700">{status || "已保存"}</span>}
            {!saved && status && <span className="text-slate-600">{status}</span>}
            {error && <span className="text-red-600">{error}</span>}
          </div>
        }
      >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-700">当前启用的 Provider</span>
            <Select
              className="w-full"
              value={activeProvider}
              onChange={(event) => {
                setActiveProvider(event.target.value);
                setSaved(false);
                setStatus("");
                setError("");
              }}
            >
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.label}
                </option>
              ))}
            </Select>
          </label>
          <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
            <div className="font-medium text-slate-800">{activeProviderInfo?.label || "未选择"}</div>
            <div className="mt-1 truncate">{providerForms[activeProvider]?.model || ""}</div>
          </div>
        </div>

        {activeProviderInfo && (
          <article className="mt-4 rounded-lg border border-primary bg-blue-50/40 p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">{activeProviderInfo.label}</h3>
                  <span className="rounded bg-primary px-2 py-0.5 text-xs text-white">当前使用</span>
                  {activeProviderInfo.api_key_configured && (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                      <CheckCircle2 size={13} />
                      Key 已配置
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {providerTypeLabel(activeProviderInfo.provider_type)}
                  {!activeProviderInfo.requires_api_key ? "，可不填 Key" : ""}
                </p>
              </div>
              {activeProviderInfo.docs_url && (
                <a
                  href={activeProviderInfo.docs_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  文档
                  <ExternalLink size={12} />
                </a>
              )}
            </div>

            <div className="grid gap-3 lg:grid-cols-3">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">API Key</span>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3 top-2.5 text-slate-400" size={15} />
                  <Input
                    className="pl-9"
                    type="password"
                    placeholder={
                      activeProviderInfo.api_key_configured
                        ? "已配置，留空不修改"
                        : activeProviderInfo.requires_api_key
                          ? "请输入 API Key"
                          : "可选"
                    }
                    value={activeForm.api_key}
                    onChange={(event) => updateProviderField(activeProviderInfo.id, "api_key", event.target.value)}
                  />
                </div>
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">Base URL</span>
                <Input
                  value={activeForm.base_url}
                  onChange={(event) => updateProviderField(activeProviderInfo.id, "base_url", event.target.value)}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">模型名称</span>
                <Select
                  className="w-full"
                  value={activeForm.model}
                  onChange={(event) => updateProviderField(activeProviderInfo.id, "model", event.target.value)}
                >
                  <option value={activeForm.model}>{activeForm.model || "请先识别模型"}</option>
                  {(modelOptions[activeProviderInfo.id] || []).filter((model) => model !== activeForm.model).map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </Select>
              </label>
            </div>
            <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">手动模型名</span>
                <Input
                  placeholder="如果模型列表没有目标模型，可以手动填写"
                  value={activeForm.model}
                  onChange={(event) => updateProviderField(activeProviderInfo.id, "model", event.target.value)}
                />
              </label>
              <div className="flex items-end gap-2">
                <PrimaryButton onClick={detectModels} disabled={loadingModels}>
                  <ListFilter size={16} />
                  {loadingModels ? "识别中" : "识别模型"}
                </PrimaryButton>
                <Button onClick={testModel} disabled={testingModel || !activeForm.model.trim()}>
                  <Activity size={16} />
                  {testingModel ? "测试中" : "测试模型"}
                </Button>
                <PrimaryButton onClick={saveSettings} disabled={saving || !activeProviderInfo}>
                  <Save size={16} />
                  {saving ? "保存中" : "保存模型配置"}
                </PrimaryButton>
              </div>
            </div>
            {activeProviderInfo.note && <p className="mt-3 text-xs leading-5 text-slate-500">{activeProviderInfo.note}</p>}
          </article>
        )}

        <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-200 pt-4">
          <p className="text-sm text-slate-500">先填 API Key 并识别模型，再选择或手动填写模型名。点击保存后，回复工作台会立即使用当前模型。</p>
          <PrimaryButton onClick={saveSettings} disabled={saving || !activeProviderInfo}>
            <Save size={16} />
            {saving ? "保存中" : "保存模型配置"}
          </PrimaryButton>
        </div>
      </Panel>

      <Panel title="回复边界">
        <div className="text-sm leading-6 text-slate-600">
          成绩、处分、奖助学金结果、学籍状态、个人隐私、投诉申诉、情绪危机等问题会自动建议人工核实。所有 AI 回复仍需要老师确认后再复制发送。
        </div>
      </Panel>

      <Panel
        title="数据备份与恢复"
        action={
          <div className="text-xs">
            {backupStatus && <span className="text-emerald-700">{backupStatus}</span>}
            {backupError && <span className="text-red-600">{backupError}</span>}
          </div>
        }
      >
        <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto]">
          <Input
            key={backupInputKey}
            type="file"
            accept=".json"
            onChange={(event) => {
              setBackupFile(event.target.files?.[0] || null);
              setBackupStatus("");
              setBackupError("");
            }}
          />
          <Button onClick={exportBackup}>
            <Download size={16} />
            导出备份
          </Button>
          <PrimaryButton onClick={importBackup} disabled={!backupFile}>
            <Upload size={16} />
            导入备份
          </PrimaryButton>
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          备份包含 FAQ、知识库解析文本、历史记录和非密钥设置；API Key 不会导出。导入时默认追加数据，并跳过相似 FAQ。
        </p>
      </Panel>

      <Panel title="版本信息">
        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
            <div className="font-semibold text-slate-900">{appInfo?.name || "高校行政 AI 回复助手"}</div>
            <div className="mt-2 text-slate-600">版本：{appInfo?.version || "-"}</div>
            <div className="mt-1 text-slate-600">开发者：{appInfo?.developer || "-"}</div>
          </div>
          <pre className="max-h-52 overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-white p-3 text-sm leading-6 text-slate-600">
            {appInfo?.latest_update || "暂无更新信息。"}
          </pre>
        </div>
      </Panel>

      <Panel title="后续 TODO">
        <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-slate-600">
          <li>生产环境建议对 API Key 增加加密存储或接入密钥管理服务。</li>
          <li>部分厂商可能不开放 `/models`，识别失败时可用控制台模型名手动保存。</li>
          <li>增加向量检索，可替换为 Chroma、FAISS 或 pgvector。</li>
        </ul>
      </Panel>
    </div>
  );
}

function providerTypeLabel(providerType: string) {
  if (providerType === "ollama_native") return "Ollama 原生接口";
  if (providerType === "anthropic_native") return "Anthropic 原生接口";
  if (providerType === "gemini_native") return "Gemini 原生接口";
  return "OpenAI 兼容接口";
}
