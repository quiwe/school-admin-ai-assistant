package com.quiwe.schooladminaiassistant.models

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

val apiJson = Json {
    ignoreUnknownKeys = true
    encodeDefaults = true
    coerceInputValues = true
}

// ── Reply ──

@Serializable
data class GenerateReplyRequest(
    val question: String,
    val style: String = "normal"
)

@Serializable
data class Reference(
    val title: String,
    val content: String
)

@Serializable
data class ReplyResponse(
    val answer: String,
    val category: String,
    val confidence: Double,
    @SerialName("need_human_review") val needHumanReview: Boolean,
    val references: List<Reference> = emptyList(),
    @SerialName("ai_used") val aiUsed: Boolean = false,
    @SerialName("ai_provider") val aiProvider: String? = null,
    @SerialName("ai_model") val aiModel: String? = null,
    @SerialName("ai_error") val aiError: String? = null,
    @SerialName("prompt_tokens") val promptTokens: Int? = null,
    @SerialName("completion_tokens") val completionTokens: Int? = null,
    @SerialName("total_tokens") val totalTokens: Int? = null,
    @SerialName("prompt_cache_hit_tokens") val promptCacheHitTokens: Int? = null,
    @SerialName("prompt_cache_miss_tokens") val promptCacheMissTokens: Int? = null,
    @SerialName("cache_hit_ratio") val cacheHitRatio: Double? = null,
    @SerialName("cost_usd") val costUsd: Double? = null,
    @SerialName("cost_cny") val costCny: Double? = null
)

@Serializable
data class RewriteRequest(
    val question: String,
    val answer: String,
    val style: String = "formal"
)

@Serializable
data class RewriteResponse(
    val answer: String,
    @SerialName("ai_used") val aiUsed: Boolean = false,
    @SerialName("prompt_tokens") val promptTokens: Int? = null,
    @SerialName("completion_tokens") val completionTokens: Int? = null,
    @SerialName("total_tokens") val totalTokens: Int? = null,
    @SerialName("prompt_cache_hit_tokens") val promptCacheHitTokens: Int? = null,
    @SerialName("prompt_cache_miss_tokens") val promptCacheMissTokens: Int? = null,
    @SerialName("cache_hit_ratio") val cacheHitRatio: Double? = null,
    @SerialName("cost_usd") val costUsd: Double? = null,
    @SerialName("cost_cny") val costCny: Double? = null
)

// ── Student ──

@Serializable
data class StudentReplyRequest(
    val question: String,
    val style: String = "normal"
)

@Serializable
data class StudentReplyResponse(
    val answer: String,
    val category: String,
    @SerialName("need_human_review") val needHumanReview: Boolean = false
)

// ── Knowledge ──

@Serializable
data class KnowledgeFileResponse(
    val id: Long,
    val filename: String,
    val category: String,
    @SerialName("upload_time") val uploadTime: String,
    @SerialName("parsed_text") val parsedText: String,
    @SerialName("chunk_count") val chunkCount: Int,
    val status: String
)

@Serializable
data class KnowledgeUpdateRequest(
    val category: String? = null
)

// ── FAQ ──

@Serializable
data class FaqCreateRequest(
    val question: String,
    val answer: String,
    val category: String = "其他",
    @SerialName("allow_auto_reply") val allowAutoReply: Boolean = true,
    val force: Boolean = false
)

@Serializable
data class FaqUpdateRequest(
    val question: String? = null,
    val answer: String? = null,
    val category: String? = null,
    @SerialName("allow_auto_reply") val allowAutoReply: Boolean? = null
)

@Serializable
data class FaqItemResponse(
    val id: Long,
    val question: String,
    val answer: String,
    val category: String,
    @SerialName("allow_auto_reply") val allowAutoReply: Boolean,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)

@Serializable
data class FaqImportResponse(
    val imported: Int,
    @SerialName("skipped_duplicates") val skippedDuplicates: Int = 0
)

// ── History ──

@Serializable
data class HistoryCreateRequest(
    @SerialName("student_question") val studentQuestion: String,
    @SerialName("ai_answer") val aiAnswer: String,
    @SerialName("final_answer") val finalAnswer: String,
    val category: String = "其他",
    val confidence: Double = 0.0,
    @SerialName("need_human_review") val needHumanReview: Boolean = false,
    @SerialName("cost_cny") val costCny: Double? = null,
    @SerialName("cost_usd") val costUsd: Double? = null
)

@Serializable
data class HistoryItemResponse(
    val id: Long,
    @SerialName("student_question") val studentQuestion: String,
    @SerialName("ai_answer") val aiAnswer: String,
    @SerialName("final_answer") val finalAnswer: String,
    val category: String,
    val confidence: Double,
    @SerialName("need_human_review") val needHumanReview: Boolean,
    @SerialName("cost_cny") val costCny: Double? = null,
    @SerialName("cost_usd") val costUsd: Double? = null,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class HistoryDeleteRequest(val ids: List<Long>)

@Serializable
data class DeleteResponse(val ok: Boolean, val deleted: Int = 0)

// ── Settings / AI ──

@Serializable
data class AIProviderConfigResponse(
    val id: String,
    val label: String,
    @SerialName("provider_type") val providerType: String,
    @SerialName("base_url") val baseUrl: String,
    val model: String,
    @SerialName("api_key_configured") val apiKeyConfigured: Boolean,
    @SerialName("requires_api_key") val requiresApiKey: Boolean,
    @SerialName("docs_url") val docsUrl: String? = null,
    val note: String? = null
)

@Serializable
data class AIProviderConfigUpdate(
    val id: String,
    @SerialName("api_key") val apiKey: String? = null,
    @SerialName("base_url") val baseUrl: String? = null,
    val model: String? = null
)

@Serializable
data class AISettingsResponse(
    @SerialName("ai_provider") val aiProvider: String,
    val providers: List<AIProviderConfigResponse>
)

@Serializable
data class AISettingsUpdateRequest(
    @SerialName("ai_provider") val aiProvider: String,
    val providers: List<AIProviderConfigUpdate> = emptyList()
)

@Serializable
data class AIModelListRequest(
    @SerialName("provider_id") val providerId: String,
    @SerialName("api_key") val apiKey: String? = null,
    @SerialName("base_url") val baseUrl: String? = null
)

@Serializable
data class AIModelListResponse(
    val models: List<String>,
    val source: String
)

@Serializable
data class AIProviderTestRequest(
    @SerialName("provider_id") val providerId: String,
    @SerialName("api_key") val apiKey: String? = null,
    @SerialName("base_url") val baseUrl: String? = null,
    val model: String? = null
)

@Serializable
data class AIProviderTestResponse(
    val ok: Boolean,
    val message: String,
    @SerialName("latency_ms") val latencyMs: Long,
    val preview: String = ""
)

// ── QQ / WeCom (stubs for Android) ──

@Serializable
data class QQSettingsResponse(
    val enabled: Boolean = false,
    @SerialName("app_id") val appId: String = "",
    @SerialName("app_secret_configured") val appSecretConfigured: Boolean = false,
    val sandbox: Boolean = false,
    @SerialName("owner_openid") val ownerOpenid: String = "",
    val allowlist: List<String> = emptyList(),
    val running: Boolean = false
)

@Serializable
data class WeComSettingsResponse(
    val enabled: Boolean = false,
    @SerialName("bot_id") val botId: String = "",
    @SerialName("secret_configured") val secretConfigured: Boolean = false,
    val allowlist: List<String> = emptyList(),
    val running: Boolean = false
)

// ── Data ──

@Serializable
data class BackupImportResponse(
    val ok: Boolean,
    @SerialName("imported_faq") val importedFaq: Int = 0,
    @SerialName("skipped_faq_duplicates") val skippedFaqDuplicates: Int = 0,
    @SerialName("imported_knowledge_files") val importedKnowledgeFiles: Int = 0,
    @SerialName("imported_history") val importedHistory: Int = 0
)

// ── App ──

@Serializable
data class AppInfoResponse(
    val name: String,
    val version: String,
    val developer: String,
    @SerialName("latest_update") val latestUpdate: String
)

@Serializable
data class StudentLinkResponse(val url: String)

@Serializable
data class AdminLinkResponse(
    val url: String,
    @SerialName("api_base") val apiBase: String,
    @SerialName("admin_access_key") val adminAccessKey: String
)

@Serializable
data class CostStatsResponse(
    @SerialName("total_spent_cny") val totalSpentCny: Double = 0.0,
    @SerialName("monthly_budget_cny") val monthlyBudgetCny: Double? = null,
    @SerialName("remaining_cny") val remainingCny: Double? = null
)

@Serializable
data class BudgetRequest(
    @SerialName("monthly_budget_cny") val monthlyBudgetCny: Double? = null
)

@Serializable
data class AutoStartResponse(
    val enabled: Boolean = true,
    @SerialName("current_enabled") val currentEnabled: Boolean = false,
    val supported: Boolean = false,
    @SerialName("target_path") val targetPath: String = "",
    val message: String = ""
)

// Update stubs
@Serializable
data class UpdateCheckResponse(
    @SerialName("current_version") val currentVersion: String,
    @SerialName("latest_version") val latestVersion: String = "",
    @SerialName("has_update") val hasUpdate: Boolean = false,
    @SerialName("release_url") val releaseUrl: String = "",
    @SerialName("asset_name") val assetName: String? = null,
    @SerialName("download_url") val downloadUrl: String? = null,
    @SerialName("asset_size") val assetSize: Long? = null,
    val digest: String? = null,
    @SerialName("published_at") val publishedAt: String? = null,
    val body: String = "",
    @SerialName("min_supported_version") val minSupportedVersion: String? = null,
    @SerialName("force_update") val forceUpdate: Boolean = false,
    @SerialName("update_required_message") val updateRequiredMessage: String? = null,
    @SerialName("update_source") val updateSource: String? = null
)

@Serializable
data class UpdateProgressResponse(
    val status: String = "idle",
    val phase: String = "idle",
    val message: String = "",
    @SerialName("bytes_downloaded") val bytesDownloaded: Long = 0,
    @SerialName("bytes_total") val bytesTotal: Long? = null,
    val percent: Double = 0.0,
    @SerialName("latest_version") val latestVersion: String? = null,
    @SerialName("asset_name") val assetName: String? = null,
    @SerialName("installer_path") val installerPath: String? = null,
    val error: String? = null
)
