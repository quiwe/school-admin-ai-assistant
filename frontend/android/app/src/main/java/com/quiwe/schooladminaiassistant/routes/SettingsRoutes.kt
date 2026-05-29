package com.quiwe.schooladminaiassistant.routes

import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import com.quiwe.schooladminaiassistant.services.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit
import kotlinx.serialization.json.*

class SettingsRoutes(
    private val settingDao: SettingDao,
    private val aiProvider: AiProviderService
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    // ── AI Settings ──

    suspend fun getAISettings(): String {
        val providerId = normalizeProviderId(settingDao.getByKey("ai_provider")?.value)
        val configs = PROVIDER_PRESETS.map { preset ->
            val baseUrl = settingDao.getByKey(providerSettingKey(preset.id, "base_url"))?.value
                ?: preset.defaultBaseUrl
            val model = settingDao.getByKey(providerSettingKey(preset.id, "model"))?.value
                ?: preset.defaultModel
            val hasKey = settingDao.getByKey(providerSettingKey(preset.id, "api_key"))?.value != null
            AIProviderConfigResponse(
                id = preset.id,
                label = preset.label,
                providerType = preset.providerType,
                baseUrl = baseUrl,
                model = model,
                apiKeyConfigured = hasKey,
                requiresApiKey = preset.requiresApiKey,
                docsUrl = preset.docsUrl,
                note = preset.note
            )
        }
        val res = AISettingsResponse(aiProvider = providerId, providers = configs)
        return apiJson.encodeToString(AISettingsResponse.serializer(), res)
    }

    suspend fun updateAISettings(body: String): String {
        val req = apiJson.decodeFromString<AISettingsUpdateRequest>(body)
        val provider = normalizeProviderId(req.aiProvider)
        settingDao.upsert(SettingEntity(key = "ai_provider", value = provider))

        for (pc in req.providers) {
            val pid = normalizeProviderId(pc.id)
            val preset = PROVIDER_MAP[pid]!!
            pc.baseUrl?.let {
                settingDao.upsert(SettingEntity(key = providerSettingKey(pid, "base_url"), value = it.trim().ifEmpty { preset.defaultBaseUrl }))
            }
            pc.model?.let {
                settingDao.upsert(SettingEntity(key = providerSettingKey(pid, "model"), value = it.trim().ifEmpty { preset.defaultModel }))
            }
            pc.apiKey?.trim()?.let {
                if (it.isNotEmpty()) settingDao.upsert(SettingEntity(key = providerSettingKey(pid, "api_key"), value = it))
            }
        }
        return getAISettings()
    }

    suspend fun listModels(body: String): String {
        val req = apiJson.decodeFromString<AIModelListRequest>(body)
        val pid = normalizeProviderId(req.providerId)
        val preset = PROVIDER_MAP[pid]!!
        val baseUrl = req.baseUrl?.trim()?.ifEmpty { null }
            ?: settingDao.getByKey(providerSettingKey(pid, "base_url"))?.value
            ?: preset.defaultBaseUrl
        val apiKey = req.apiKey?.trim()?.ifEmpty { null }
            ?: settingDao.getByKey(providerSettingKey(pid, "api_key"))?.value

        val models = try {
            discoverModels(preset, baseUrl, apiKey)
        } catch (e: Exception) {
            return """{"detail":"${e.message}"}"""
        }
        val source = if (models.isNotEmpty()) "api" else "preset"
        val res = AIModelListResponse(models = models, source = source)
        return apiJson.encodeToString(AIModelListResponse.serializer(), res)
    }

    suspend fun testProvider(body: String): String {
        val req = apiJson.decodeFromString<AIProviderTestRequest>(body)
        val pid = normalizeProviderId(req.providerId)
        val preset = PROVIDER_MAP[pid]!!
        val baseUrl = req.baseUrl?.trim()?.ifEmpty { null }
            ?: settingDao.getByKey(providerSettingKey(pid, "base_url"))?.value
            ?: preset.defaultBaseUrl
        val apiKey = req.apiKey?.trim()?.ifEmpty { null }
            ?: settingDao.getByKey(providerSettingKey(pid, "api_key"))?.value
        val model = req.model?.trim()?.ifEmpty { null }
            ?: settingDao.getByKey(providerSettingKey(pid, "model"))?.value
            ?: preset.defaultModel

        val config = AiConfig(
            aiProvider = pid,
            providerType = preset.providerType,
            apiKey = apiKey,
            model = model,
            baseUrl = baseUrl
        )

        val start = System.currentTimeMillis()
        return try {
            val result = aiProvider.chat("请用一句话介绍你自己。", config)
            val latency = System.currentTimeMillis() - start
            val res = AIProviderTestResponse(
                ok = true,
                message = "连接成功",
                latencyMs = latency,
                preview = result.text.take(200)
            )
            apiJson.encodeToString(AIProviderTestResponse.serializer(), res)
        } catch (e: Exception) {
            val latency = System.currentTimeMillis() - start
            val res = AIProviderTestResponse(
                ok = false,
                message = e.message ?: "连接失败",
                latencyMs = latency
            )
            apiJson.encodeToString(AIProviderTestResponse.serializer(), res)
        }
    }

    private fun discoverModels(preset: ProviderPreset, baseUrl: String, apiKey: String?): List<String> {
        return when (preset.providerType) {
            "ollama_native" -> {
                val req = Request.Builder().url("${baseUrl.trimEnd('/')}/api/tags").build()
                val resp = client.newCall(req).execute()
                val json = Json.parseToJsonElement(resp.body?.string() ?: "{}").jsonObject
                json["models"]?.jsonArray?.mapNotNull { it.jsonObject["name"]?.jsonPrimitive?.content } ?: emptyList()
            }
            else -> {
                val body = "{}".toRequestBody(jsonMediaType)
                val req = Request.Builder()
                    .url("${baseUrl.trimEnd('/')}/models")
                    .header("Authorization", "Bearer ${apiKey ?: "not-needed"}")
                    .get()
                    .build()
                try {
                    val resp = client.newCall(req).execute()
                    val json = Json.parseToJsonElement(resp.body?.string() ?: "{}").jsonObject
                    json["data"]?.jsonArray?.mapNotNull { it.jsonObject["id"]?.jsonPrimitive?.content }
                        ?.distinct() ?: emptyList()
                } catch (_: Exception) {
                    listOf(preset.defaultModel)
                }
            }
        }
    }

    // ── QQ / WeCom Stubs ──

    suspend fun getQQSettings(): String {
        val res = QQSettingsResponse()
        return apiJson.encodeToString(QQSettingsResponse.serializer(), res)
    }

    suspend fun updateQQSettings(): String {
        val res = QQSettingsResponse()
        return apiJson.encodeToString(QQSettingsResponse.serializer(), res)
    }

    suspend fun getWeComSettings(): String {
        val res = WeComSettingsResponse()
        return apiJson.encodeToString(WeComSettingsResponse.serializer(), res)
    }

    suspend fun updateWeComSettings(): String {
        val res = WeComSettingsResponse()
        return apiJson.encodeToString(WeComSettingsResponse.serializer(), res)
    }

    // ── Cost Stats ──

    suspend fun getCostStats(): String {
        val totalSpent = (settingDao.getByKey("total_spent_cny")?.value?.toDoubleOrNull() ?: 0.0)
        val budget = settingDao.getByKey("monthly_budget_cny")?.value?.toDoubleOrNull()
        val remaining = budget?.let { it - totalSpent }
        val res = CostStatsResponse(
            totalSpentCny = Math.round(totalSpent * 100.0) / 100.0,
            monthlyBudgetCny = budget?.let { Math.round(it * 100.0) / 100.0 },
            remainingCny = remaining?.let { Math.round(it * 100.0) / 100.0 }
        )
        return apiJson.encodeToString(CostStatsResponse.serializer(), res)
    }

    suspend fun updateBudget(body: String): String {
        val req = apiJson.decodeFromString<BudgetRequest>(body)
        if (req.monthlyBudgetCny != null) {
            settingDao.upsert(SettingEntity(key = "monthly_budget_cny", value = req.monthlyBudgetCny.toString()))
        } else {
            settingDao.deleteByKey("monthly_budget_cny")
        }
        return getCostStats()
    }

    suspend fun getAutoStart(): String {
        val res = AutoStartResponse(supported = false, message = "安卓端无需此设置")
        return apiJson.encodeToString(AutoStartResponse.serializer(), res)
    }

    suspend fun updateAutoStart(): String {
        val res = AutoStartResponse(supported = false, message = "安卓端无需此设置")
        return apiJson.encodeToString(AutoStartResponse.serializer(), res)
    }
}
