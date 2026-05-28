package com.quiwe.schooladminaiassistant.services

data class ProviderPreset(
    val id: String,
    val label: String,
    val providerType: String,
    val defaultBaseUrl: String,
    val defaultModel: String,
    val requiresApiKey: Boolean = true,
    val docsUrl: String? = null,
    val note: String? = null
)

data class AiConfig(
    val aiProvider: String,
    val providerType: String,
    val apiKey: String?,
    val model: String,
    val baseUrl: String
)

val PROVIDER_PRESETS = listOf(
    ProviderPreset("openai", "OpenAI", "openai_compatible", "https://api.openai.com/v1", "gpt-4o-mini", docsUrl = "https://platform.openai.com/docs"),
    ProviderPreset("deepseek", "DeepSeek", "openai_compatible", "https://api.deepseek.com", "deepseek-v4-flash", docsUrl = "https://api-docs.deepseek.com/"),
    ProviderPreset("anthropic", "Claude / Anthropic", "anthropic_native", "https://api.anthropic.com/v1", "claude-sonnet-4-20250514", docsUrl = "https://docs.anthropic.com/en/docs/about-claude/models/all-models"),
    ProviderPreset("gemini", "Google Gemini", "gemini_native", "https://generativelanguage.googleapis.com/v1beta", "gemini-2.5-flash", docsUrl = "https://ai.google.dev/gemini-api/docs/models"),
    ProviderPreset("qwen", "通义千问 / 阿里百炼", "openai_compatible", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", docsUrl = "https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api", note = "不同地域的 API Key 和 Base URL 可能不同。"),
    ProviderPreset("zhipu", "智谱 GLM", "openai_compatible", "https://open.bigmodel.cn/api/paas/v4", "glm-4.5", docsUrl = "https://docs.bigmodel.cn/"),
    ProviderPreset("kimi", "Kimi / Moonshot", "openai_compatible", "https://api.moonshot.ai/v1", "kimi-latest", docsUrl = "https://platform.kimi.ai/docs/api/overview"),
    ProviderPreset("doubao", "豆包 / 火山方舟", "openai_compatible", "https://ark.cn-beijing.volces.com/api/v3", "doubao-seed-1-6-flash", docsUrl = "https://www.volcengine.com/docs/82379", note = "模型名通常可填写火山方舟推理接入点 ID。"),
    ProviderPreset("hunyuan", "腾讯混元", "openai_compatible", "https://api.hunyuan.cloud.tencent.com/v1", "hunyuan-turbos-latest", docsUrl = "https://cloud.tencent.com/document/product/1729/97732"),
    ProviderPreset("siliconflow", "硅基流动 SiliconFlow", "openai_compatible", "https://api.siliconflow.cn/v1", "Qwen/Qwen3-32B", docsUrl = "https://docs.siliconflow.com/"),
    ProviderPreset("minimax", "MiniMax", "openai_compatible", "https://api.minimax.io/v1", "MiniMax-M2.7", docsUrl = "https://platform.minimax.io/docs/api-reference/text-chat"),
    ProviderPreset("mistral", "Mistral AI", "openai_compatible", "https://api.mistral.ai/v1", "mistral-large-latest", docsUrl = "https://docs.mistral.ai/api/"),
    ProviderPreset("cohere", "Cohere", "openai_compatible", "https://api.cohere.com/compatibility/v1", "command-a-03-2025", docsUrl = "https://docs.cohere.com/v2/docs/models"),
    ProviderPreset("pangu", "华为云盘古 / ModelArts", "openai_compatible", "https://infer-modelarts-cn-southwest-2.modelarts-infer.com/api/v2", "请输入部署模型名", docsUrl = "https://support.huaweicloud.com/api-pangulm/pangulm_05_0079.html", note = "华为云不同区域和部署的 Base URL、模型名可能不同。"),
    ProviderPreset("xiaomi", "小米 MiMo", "openai_compatible", "https://api.xiaomimimo.com/v1", "xiaomi/mimo-v2-flash", docsUrl = "https://mimo.xiaomi.com/"),
    ProviderPreset("openrouter", "OpenRouter", "openai_compatible", "https://openrouter.ai/api/v1", "openai/gpt-4o-mini", docsUrl = "https://openrouter.ai/docs/quickstart"),
    ProviderPreset("ollama", "Ollama 本地模型", "ollama_native", "http://localhost:11434", "llama3.1", requiresApiKey = false, docsUrl = "https://github.com/ollama/ollama/blob/main/docs/api.md"),
    ProviderPreset("lmstudio", "LM Studio 本地模型", "openai_compatible", "http://localhost:1234/v1", "local-model", requiresApiKey = false, docsUrl = "https://lmstudio.ai/docs/api"),
    ProviderPreset("custom", "自定义 OpenAI 兼容接口", "openai_compatible", "http://localhost:8001/v1", "custom-model", requiresApiKey = false, note = "适合学校私有网关、One API、New API、LiteLLM 等兼容服务。")
)

val PROVIDER_MAP: Map<String, ProviderPreset> = PROVIDER_PRESETS.associateBy { it.id }

fun normalizeProviderId(providerId: String?): String {
    if (providerId == "local") return "ollama"
    return if (providerId != null && PROVIDER_MAP.containsKey(providerId)) providerId else "openai"
}

fun providerSettingKey(providerId: String, field: String): String = "provider_${providerId}_$field"
