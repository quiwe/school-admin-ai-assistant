import { Activity, Bot, CheckCircle2, Copy, Download, ExternalLink, KeyRound, Link2, ListFilter, Power, Save, Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  api,
  AdminLinkResponse,
  AIProviderConfig,
  AISettingsUpdate,
  AppInfo,
  AutoStartSettings,
  CostStats,
  QQSettingsUpdate,
  WeComSettingsUpdate
} from "../api/client";
import { Button, Input, Panel, PrimaryButton, Select, Textarea } from "../components/ui";
import { copyToClipboard } from "../utils/clipboard";

type ProviderForm = {
  api_key: string;
  base_url: string;
  model: string;
};

type QQForm = {
  enabled: boolean;
  app_id: string;
  app_secret: string;
  app_secret_configured: boolean;
  sandbox: boolean;
  owner_openid: string;
  allowlist_text: string;
  running: boolean;
};

type WeComForm = {
  enabled: boolean;
  bot_id: string;
  secret: string;
  secret_configured: boolean;
  allowlist_text: string;
  running: boolean;
  last_error: string;
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
  const [qqForm, setQQForm] = useState<QQForm>({
    enabled: false,
    app_id: "",
    app_secret: "",
    app_secret_configured: false,
    sandbox: false,
    owner_openid: "",
    allowlist_text: "",
    running: false
  });
  const [savingQQ, setSavingQQ] = useState(false);
  const [qqStatus, setQQStatus] = useState("");
  const [qqError, setQQError] = useState("");

  const [activeChannel, setActiveChannel] = useState<"wecom" | "qq">("wecom");
  const [wecomForm, setWeComForm] = useState<WeComForm>({
    enabled: false,
    bot_id: "",
    secret: "",
    secret_configured: false,
    allowlist_text: "",
    running: false,
    last_error: ""
  });
  const [savingWeCom, setSavingWeCom] = useState(false);
  const [wecomStatus, setWeComStatus] = useState("");
  const [wecomError, setWeComError] = useState("");

  const [costStats, setCostStats] = useState<CostStats | null>(null);
  const [budgetInput, setBudgetInput] = useState("");
  const [budgetSaving, setBudgetSaving] = useState(false);
  const [budgetStatus, setBudgetStatus] = useState("");
  const [autoStart, setAutoStart] = useState<AutoStartSettings | null>(null);
  const [savingAutoStart, setSavingAutoStart] = useState(false);
  const [autoStartStatus, setAutoStartStatus] = useState("");
  const [adminLink, setAdminLink] = useState<AdminLinkResponse | null>(null);
  const [adminLinkStatus, setAdminLinkStatus] = useState("");

  useEffect(() => {
    loadSettings();
    loadQQSettings();
    loadWeComSettings();
    loadCostStats();
    loadAutoStartSettings();
    loadAdminLink();
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

  async function loadQQSettings() {
    try {
      const data = await api.getQQSettings();
      setQQForm({
        enabled: data.enabled,
        app_id: data.app_id,
        app_secret: "",
        app_secret_configured: data.app_secret_configured,
        sandbox: data.sandbox,
        owner_openid: data.owner_openid,
        allowlist_text: data.allowlist.join("\n"),
        running: data.running
      });
      setQQStatus("");
      setQQError("");
    } catch (err) {
      setQQError(err instanceof Error ? err.message : "读取 QQ Bot 设置失败");
    }
  }

  async function loadWeComSettings() {
    try {
      const data = await api.getWeComSettings();
      setWeComForm({
        enabled: data.enabled,
        bot_id: data.bot_id,
        secret: "",
        secret_configured: data.secret_configured,
        allowlist_text: data.allowlist.join("\n"),
        running: data.running,
        last_error: data.last_error || ""
      });
      setWeComStatus("");
      setWeComError("");
    } catch (err) {
      setWeComError(err instanceof Error ? err.message : "读取企业微信设置失败");
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

  function updateQQField<K extends keyof QQForm>(field: K, value: QQForm[K]) {
    setQQStatus("");
    setQQError("");
    setQQForm((current) => ({ ...current, [field]: value }));
  }

  async function saveQQSettings() {
    setQQStatus("");
    setQQError("");
    const appId = qqForm.app_id.trim();
    if (qqForm.enabled && !appId) {
      setQQError("启用 QQ Bot 前请填写 AppID");
      return;
    }
    if (qqForm.enabled && !qqForm.app_secret.trim() && !qqForm.app_secret_configured) {
      setQQError("启用 QQ Bot 前请填写 AppSecret");
      return;
    }
    setSavingQQ(true);
    try {
      const payload: QQSettingsUpdate = {
        enabled: qqForm.enabled,
        app_id: appId,
        ...(qqForm.app_secret.trim() ? { app_secret: qqForm.app_secret.trim() } : {}),
        sandbox: qqForm.sandbox,
        owner_openid: qqForm.owner_openid.trim(),
        allowlist: qqForm.allowlist_text
          .split(/[\n,\s]+/)
          .map((item) => item.trim())
          .filter(Boolean)
      };
      const data = await api.updateQQSettings(payload);
      setQQForm({
        enabled: data.enabled,
        app_id: data.app_id,
        app_secret: "",
        app_secret_configured: data.app_secret_configured,
        sandbox: data.sandbox,
        owner_openid: data.owner_openid,
        allowlist_text: data.allowlist.join("\n"),
        running: data.running
      });
      setQQStatus(data.enabled ? (data.running ? "QQ Bot 已保存并启动" : "已保存，但机器人尚未启动") : "QQ Bot 已保存并停用");
    } catch (err) {
      setQQError(err instanceof Error ? err.message : "保存 QQ Bot 设置失败");
    } finally {
      setSavingQQ(false);
    }
  }

  function updateWeComField<K extends keyof WeComForm>(field: K, value: WeComForm[K]) {
    setWeComStatus("");
    setWeComError("");
    setWeComForm((current) => ({ ...current, [field]: value }));
  }

  async function saveWeComSettings() {
    setWeComStatus("");
    setWeComError("");
    const botId = wecomForm.bot_id.trim();
    if (wecomForm.enabled && !botId) {
      setWeComError("启用企业微信前请填写 Bot ID");
      return;
    }
    if (wecomForm.enabled && !wecomForm.secret.trim() && !wecomForm.secret_configured) {
      setWeComError("启用企业微信前请填写 Secret");
      return;
    }
    setSavingWeCom(true);
    try {
      const payload: WeComSettingsUpdate = {
        enabled: wecomForm.enabled,
        bot_id: botId,
        ...(wecomForm.secret.trim() ? { secret: wecomForm.secret.trim() } : {}),
        allowlist: wecomForm.allowlist_text
          .split(/[\n,\s]+/)
          .map((item) => item.trim())
          .filter(Boolean)
      };
      const data = await api.updateWeComSettings(payload);
      setWeComForm({
        enabled: data.enabled,
        bot_id: data.bot_id,
        secret: "",
        secret_configured: data.secret_configured,
        allowlist_text: data.allowlist.join("\n"),
        running: data.running,
        last_error: data.last_error || ""
      });
      setWeComStatus(data.enabled ? (data.running ? "企业微信已保存并启动" : "已保存，机器人连接中...") : "企业微信已保存并停用");
    } catch (err) {
      setWeComError(err instanceof Error ? err.message : "保存企业微信设置失败");
    } finally {
      setSavingWeCom(false);
    }
  }

  async function loadCostStats() {
    try {
      const stats = await api.getCostStats();
      setCostStats(stats);
      setBudgetInput(stats.monthly_budget_cny != null ? String(stats.monthly_budget_cny) : "");
    } catch {
      // 静默失败
    }
  }

  async function saveBudget() {
    setBudgetStatus("");
    setBudgetSaving(true);
    try {
      const value = budgetInput.trim() ? parseFloat(budgetInput.trim()) : null;
      if (value != null && (isNaN(value) || value < 0)) {
        setBudgetStatus("请输入有效的正数金额");
        return;
      }
      await api.updateBudget(value);
      await loadCostStats();
      setBudgetStatus(value != null ? `月度预算已设为 ¥${value}` : "已取消月度预算限制");
    } catch (err) {
      setBudgetStatus(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBudgetSaving(false);
    }
  }

  async function loadAutoStartSettings() {
    try {
      const data = await api.getAutoStartSettings();
      setAutoStart(data);
      setAutoStartStatus("");
    } catch (err) {
      setAutoStartStatus(err instanceof Error ? err.message : "读取开机自启动设置失败");
    }
  }

  async function saveAutoStartSettings() {
    if (!autoStart) return;
    setSavingAutoStart(true);
    setAutoStartStatus("");
    try {
      const data = await api.updateAutoStartSettings(autoStart.enabled);
      setAutoStart(data);
      setAutoStartStatus(data.enabled ? "已开启开机自启动" : "已取消开机自启动");
    } catch (err) {
      setAutoStartStatus(err instanceof Error ? err.message : "保存开机自启动设置失败");
    } finally {
      setSavingAutoStart(false);
    }
  }

  async function loadAdminLink() {
    try {
      const data = await api.getAdminLink();
      setAdminLink(data);
    } catch {
      // 移动端连接信息只在桌面端可用，失败时不影响其他设置。
    }
  }

  async function copyText(text: string, statusText: string) {
    if (!text) return;
    await copyToClipboard(text);
    setAdminLinkStatus(statusText);
    setTimeout(() => setAdminLinkStatus(""), 1500);
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

      <Panel
        title="月度 AI 预算"
        action={
          <div className="text-xs">
            {costStats ? (
              <span>
                已花费 <span className="font-medium text-blue-700">¥{costStats.total_spent_cny.toFixed(4)}</span>
                {costStats.monthly_budget_cny != null ? (
                  <span>
                    {" · "}剩余{" "}
                    <span className={costStats.remaining_cny != null && costStats.remaining_cny < 0 ? "font-medium text-red-600" : "font-medium text-emerald-600"}>
                      ¥{costStats.remaining_cny?.toFixed(2)}
                    </span>
                  </span>
                ) : (
                  <span className="text-slate-400"> · 未设预算</span>
                )}
              </span>
            ) : null}
            {budgetStatus && <span className="ml-2 text-emerald-700">{budgetStatus}</span>}
          </div>
        }
      >
        <div className="flex items-end gap-3">
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-700">月度预算金额（元）</span>
            <Input
              type="number"
              min="0"
              step="0.01"
              placeholder="留空表示不限制"
              className="w-48"
              value={budgetInput}
              onChange={(event) => {
                setBudgetInput(event.target.value);
                setBudgetStatus("");
              }}
            />
          </label>
          <PrimaryButton onClick={saveBudget} disabled={budgetSaving}>
            <Save size={16} />
            {budgetSaving ? "保存中" : "保存预算"}
          </PrimaryButton>
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          设置月度 AI 调用预算上限后，回复工作台会显示剩余余额。超支时余额数字会变红提醒。留空则不限制。
        </p>
      </Panel>

      <Panel
        title="开机自启动"
        action={
          <div className="text-xs">
            {autoStartStatus && (
              <span className={autoStartStatus.includes("失败") ? "text-red-600" : "text-emerald-700"}>
                {autoStartStatus}
              </span>
            )}
          </div>
        }
      >
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input
                type="checkbox"
                checked={autoStart?.enabled ?? true}
                onChange={(event) =>
                  setAutoStart((current) =>
                    current
                      ? { ...current, enabled: event.target.checked }
                      : {
                          enabled: event.target.checked,
                          current_enabled: false,
                          supported: false,
                          target_path: "",
                          message: ""
                        }
                  )
                }
              />
              开机后自动启动
            </label>
            <p className="text-xs leading-5 text-slate-500">
              当前系统启动项：{autoStart?.current_enabled ? "已启用" : "未启用"}
              {autoStart?.message ? `。${autoStart.message}` : ""}
            </p>
            {autoStart?.target_path && (
              <code className="block break-all rounded-md bg-slate-50 p-2 text-xs text-slate-600">
                {autoStart.target_path}
              </code>
            )}
          </div>
          <div className="flex items-start justify-end">
            <PrimaryButton onClick={saveAutoStartSettings} disabled={savingAutoStart || !autoStart?.supported}>
              <Power size={16} />
              {savingAutoStart ? "保存中" : "保存自启动设置"}
            </PrimaryButton>
          </div>
        </div>
      </Panel>

      <Panel
        title="移动端 / APK 连接"
        action={adminLinkStatus ? <span className="text-xs text-emerald-700">{adminLinkStatus}</span> : null}
      >
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <Link2 size={16} />
              完整管理地址
            </div>
            <code className="block break-all rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-700">
              {adminLink?.url || "安装版启动后会生成移动端管理地址"}
            </code>
            <div className="grid gap-2 text-xs text-slate-600 lg:grid-cols-2">
              <div className="rounded-md bg-slate-50 p-2">
                API 地址：<span className="font-mono">{adminLink?.api_base || "-"}</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-start justify-end gap-2">
            <Button onClick={() => copyText(adminLink?.url || "", "已复制完整管理地址")} disabled={!adminLink?.url}>
              <Copy size={16} />
              复制完整地址
            </Button>
          </div>
        </div>
      </Panel>

      <Panel
        title="聊天机器人"
        action={
          <div className="text-xs">
            {activeChannel === "wecom" ? (
              <>
                {wecomStatus && <span className="text-emerald-700">{wecomStatus}</span>}
                {wecomForm.last_error && (
                  <span className="text-red-600">连接异常：{wecomForm.last_error}</span>
                )}
                {wecomError && <span className="text-red-600">{wecomError}</span>}
              </>
            ) : (
              <>
                {qqStatus && <span className="text-emerald-700">{qqStatus}</span>}
                {qqError && <span className="text-red-600">{qqError}</span>}
              </>
            )}
          </div>
        }
      >
        <label className="space-y-1 text-sm">
          <span className="font-medium text-slate-700">接入渠道</span>
          <Select
            className="w-full max-w-xs"
            value={activeChannel}
            onChange={(event) => setActiveChannel(event.target.value as "wecom" | "qq")}
          >
            <option value="wecom">企业微信</option>
            <option value="qq">QQ Bot</option>
          </Select>
        </label>

        {activeChannel === "wecom" && (
          <>
            <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_240px]">
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">Bot ID</span>
                  <Input
                    placeholder="企业微信后台获取的机器人 ID"
                    value={wecomForm.bot_id}
                    onChange={(event) => updateWeComField("bot_id", event.target.value)}
                  />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">Secret</span>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-2.5 text-slate-400" size={15} />
                    <Input
                      className="pl-9"
                      type="password"
                      placeholder={wecomForm.secret_configured ? "已配置，留空不修改" : "请输入 Secret"}
                      value={wecomForm.secret}
                      onChange={(event) => updateWeComField("secret", event.target.value)}
                    />
                  </div>
                </label>
                <label className="space-y-1 text-sm lg:col-span-2">
                  <span className="font-medium text-slate-700">允许名单</span>
                  <Textarea
                    className="min-h-20"
                    placeholder="可选：多个企业微信 UserID 用空格、逗号或换行分隔，留空则允许所有人"
                    value={wecomForm.allowlist_text}
                    onChange={(event) => updateWeComField("allowlist_text", event.target.value)}
                  />
                </label>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="flex items-center gap-2 font-semibold text-slate-900">
                  <Bot size={16} />
                  {wecomForm.running ? "机器人运行中" : "机器人未运行"}
                </div>
                <label className="mt-4 flex items-center gap-2 text-slate-700">
                  <input
                    type="checkbox"
                    checked={wecomForm.enabled}
                    onChange={(event) => updateWeComField("enabled", event.target.checked)}
                  />
                  启用企业微信
                </label>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-200 pt-4">
              <p className="text-sm text-slate-500">
                使用 WebSocket 长连接，无需公网 IP。在企业微信后台创建 AI 机器人，获取 Bot ID 和 Secret 后填入上方。
              </p>
              <PrimaryButton onClick={saveWeComSettings} disabled={savingWeCom}>
                <Save size={16} />
                {savingWeCom ? "保存中" : "保存企业微信配置"}
              </PrimaryButton>
            </div>
          </>
        )}

        {activeChannel === "qq" && (
          <>
            <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_240px]">
              <div className="grid gap-3 lg:grid-cols-2">
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">AppID</span>
                  <Input
                    placeholder="QQ 机器人 AppID"
                    value={qqForm.app_id}
                    onChange={(event) => updateQQField("app_id", event.target.value)}
                  />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">AppSecret</span>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-2.5 text-slate-400" size={15} />
                    <Input
                      className="pl-9"
                      type="password"
                      placeholder={qqForm.app_secret_configured ? "已配置，留空不修改" : "请输入 AppSecret"}
                      value={qqForm.app_secret}
                      onChange={(event) => updateQQField("app_secret", event.target.value)}
                    />
                  </div>
                </label>
                <label className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">Owner OpenID</span>
                  <Input
                    placeholder="可选：只允许这个 QQ 用户使用"
                    value={qqForm.owner_openid}
                    onChange={(event) => updateQQField("owner_openid", event.target.value)}
                  />
                </label>
                <label className="space-y-1 text-sm lg:col-span-2">
                  <span className="font-medium text-slate-700">允许名单</span>
                  <Textarea
                    className="min-h-20"
                    placeholder="可选：多个 OpenID 用空格、逗号或换行分隔"
                    value={qqForm.allowlist_text}
                    onChange={(event) => updateQQField("allowlist_text", event.target.value)}
                  />
                </label>
              </div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                <div className="flex items-center gap-2 font-semibold text-slate-900">
                  <Bot size={16} />
                  {qqForm.running ? "机器人运行中" : "机器人未运行"}
                </div>
                <label className="mt-4 flex items-center gap-2 text-slate-700">
                  <input
                    type="checkbox"
                    checked={qqForm.enabled}
                    onChange={(event) => updateQQField("enabled", event.target.checked)}
                  />
                  启用 QQ Bot
                </label>
                <label className="mt-3 flex items-center gap-2 text-slate-700">
                  <input
                    type="checkbox"
                    checked={qqForm.sandbox}
                    onChange={(event) => updateQQField("sandbox", event.target.checked)}
                  />
                  使用沙箱环境
                </label>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-slate-200 pt-4">
              <p className="text-sm text-slate-500">
                点击保存后，后端会按当前配置启动或停止 QQ Bot。未填写 Owner/允许名单时，机器人会绑定首次发消息的 QQ 用户。
              </p>
              <PrimaryButton onClick={saveQQSettings} disabled={savingQQ}>
                <Save size={16} />
                {savingQQ ? "保存中" : "保存 QQ 配置"}
              </PrimaryButton>
            </div>
          </>
        )}
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
    </div>
  );
}

function providerTypeLabel(providerType: string) {
  if (providerType === "ollama_native") return "Ollama 原生接口";
  if (providerType === "anthropic_native") return "Anthropic 原生接口";
  if (providerType === "gemini_native") return "Gemini 原生接口";
  return "OpenAI 兼容接口";
}
