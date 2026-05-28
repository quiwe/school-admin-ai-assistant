package com.quiwe.schooladminaiassistant.services

import kotlinx.serialization.json.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

data class AiUsage(
    val promptTokens: Int = 0,
    val completionTokens: Int = 0,
    val totalTokens: Int = 0,
    val promptCacheHitTokens: Int = 0,
    val promptCacheMissTokens: Int = 0,
    val cacheHitRatio: Double? = null,
    val costUsd: Double? = null,
    val costCny: Double? = null
)

data class AiChatResult(
    val text: String,
    val usage: AiUsage? = null
)

private val USD_TO_CNY = 7.2

private val MODEL_PRICING_USD_PER_1M: Map<String, Map<String, Double>> = mapOf(
    "deepseek-v4-flash" to mapOf("cache_hit" to 0.0028, "cache_miss" to 0.14, "output" to 0.28),
    "deepseek-v4-pro" to mapOf("cache_hit" to 0.003625, "cache_miss" to 0.435, "output" to 0.87),
    "deepseek-chat" to mapOf("cache_hit" to 0.0028, "cache_miss" to 0.14, "output" to 0.28),
    "deepseek-reasoner" to mapOf("cache_hit" to 0.0028, "cache_miss" to 0.14, "output" to 0.28),
    "gpt-4o-mini" to mapOf("cache_hit" to 0.075, "cache_miss" to 0.15, "output" to 0.6),
    "gpt-4o" to mapOf("cache_hit" to 1.25, "cache_miss" to 2.5, "output" to 10.0)
)

class AiProviderService {
    private val client = OkHttpClient.Builder()
        .connectTimeout(90, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(90, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    private val systemPrompt: String by lazy {
        try {
            javaClass.classLoader?.getResourceAsStream("prompts/system_prompt.txt")
                ?.bufferedReader()?.readText() ?: "你是一个高校行政助手，请根据知识库内容生成回复。"
        } catch (_: Exception) {
            "你是一个高校行政助手，请根据知识库内容生成回复。"
        }
    }

    fun generateReply(question: String, references: List<Map<String, String>>, style: String, config: AiConfig): AiChatResult {
        val context = formatReferences(references)
        val userPrompt = buildString {
            append("学生问题：$question\n\n")
            append("可用依据：\n$context\n\n")
            append("回复风格：$style\n")
            append("请先判断可用依据是否能支持回答学生问题。")
            append("如果 FAQ 与学生问题只是问法不同但含义一致，可以按 FAQ 标准答案组织回复。")
            append("如果依据不能支持回答，请只说明该问题需要进一步核实。")
            append("请生成一段可直接复制到微信发送的回复。")
        }
        return chat(userPrompt, config)
    }

    fun rewriteReply(question: String, answer: String, style: String, config: AiConfig): AiChatResult {
        val styleDesc = mapOf(
            "formal" to "更正式一点，但不要生硬。",
            "shorter" to "更简短一点，保留关键信息。",
            "warmer" to "更温和一点，体现理解和安抚。"
        )[style] ?: style

        val userPrompt = buildString {
            append("学生问题：$question\n\n")
            append("当前回复：$answer\n\n")
            append("改写要求：$styleDesc\n")
            append("请只输出改写后的微信回复，不要添加解释。")
        }
        return chat(userPrompt, config)
    }

    fun chat(userPrompt: String, config: AiConfig): AiChatResult {
        return when (config.providerType) {
            "ollama_native" -> chatOllama(userPrompt, config)
            "anthropic_native" -> chatAnthropic(userPrompt, config)
            "gemini_native" -> chatGemini(userPrompt, config)
            else -> chatOpenAICompatible(userPrompt, config)
        }
    }

    private fun chatOpenAICompatible(userPrompt: String, config: AiConfig): AiChatResult {
        val body = buildJsonObject {
            put("model", config.model)
            putJsonArray("messages") {
                addJsonObject {
                    put("role", "system")
                    put("content", systemPrompt)
                }
                addJsonObject {
                    put("role", "user")
                    put("content", userPrompt)
                }
            }
            put("temperature", 0.2)
        }

        val request = Request.Builder()
            .url("${config.baseUrl.trimEnd('/')}/chat/completions")
            .header("Authorization", "Bearer ${config.apiKey ?: "not-needed"}")
            .header("Content-Type", "application/json")
            .post(body.toString().toRequestBody(jsonMediaType))
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty response")
        if (!response.isSuccessful) throw IOException("API error ${response.code}: $responseBody")

        val json = Json.parseToJsonElement(responseBody).jsonObject
        val choices = json["choices"]?.jsonArray ?: throw IOException("No choices in response")
        val content = choices[0].jsonObject["message"]?.jsonObject?.get("content")?.jsonPrimitive?.content ?: ""
        val usage = json["usage"]?.jsonObject

        return AiChatResult(text = content, usage = parseUsage(usage, config.model))
    }

    private fun chatOllama(userPrompt: String, config: AiConfig): AiChatResult {
        val body = buildJsonObject {
            put("model", config.model)
            putJsonArray("messages") {
                addJsonObject {
                    put("role", "system")
                    put("content", systemPrompt)
                }
                addJsonObject {
                    put("role", "user")
                    put("content", userPrompt)
                }
            }
            put("stream", false)
        }

        val request = Request.Builder()
            .url("${config.baseUrl.trimEnd('/')}/api/chat")
            .post(body.toString().toRequestBody(jsonMediaType))
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty response")
        if (!response.isSuccessful) throw IOException("Ollama error ${response.code}: $responseBody")

        val json = Json.parseToJsonElement(responseBody).jsonObject
        val content = json["message"]?.jsonObject?.get("content")?.jsonPrimitive?.content ?: ""

        return AiChatResult(text = content, usage = parseUsage(json, config.model))
    }

    private fun chatAnthropic(userPrompt: String, config: AiConfig): AiChatResult {
        val apiKey = config.apiKey ?: throw IOException("Claude / Anthropic 需要 API Key。")
        val body = buildJsonObject {
            put("model", config.model)
            put("max_tokens", 1200)
            put("temperature", 0.2)
            put("system", systemPrompt)
            putJsonArray("messages") {
                addJsonObject {
                    put("role", "user")
                    put("content", userPrompt)
                }
            }
        }

        val request = Request.Builder()
            .url("${config.baseUrl.trimEnd('/')}/messages")
            .header("x-api-key", apiKey)
            .header("anthropic-version", "2023-06-01")
            .header("Content-Type", "application/json")
            .post(body.toString().toRequestBody(jsonMediaType))
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty response")
        if (!response.isSuccessful) throw IOException("Anthropic error ${response.code}: $responseBody")

        val json = Json.parseToJsonElement(responseBody).jsonObject
        val contentArray = json["content"]?.jsonArray ?: buildJsonArray { }
        val text = contentArray.joinToString("") { el ->
            val obj = el.jsonObject
            if (obj["type"]?.jsonPrimitive?.content == "text") obj["text"]?.jsonPrimitive?.content ?: "" else ""
        }.trim()

        return AiChatResult(text = text, usage = parseUsage(json["usage"]?.jsonObject, config.model))
    }

    private fun chatGemini(userPrompt: String, config: AiConfig): AiChatResult {
        val apiKey = config.apiKey ?: throw IOException("Google Gemini 需要 API Key。")
        val body = buildJsonObject {
            putJsonObject("systemInstruction") {
                putJsonObject("parts") {
                    put("text", systemPrompt)
                }
            }
            putJsonArray("contents") {
                addJsonObject {
                    put("role", "user")
                    putJsonArray("parts") {
                        addJsonObject { put("text", userPrompt) }
                    }
                }
            }
            putJsonObject("generationConfig") {
                put("temperature", 0.2)
            }
        }

        val url = "${config.baseUrl.trimEnd('/')}/models/${config.model}:generateContent?key=$apiKey"
        val request = Request.Builder()
            .url(url)
            .post(body.toString().toRequestBody(jsonMediaType))
            .build()

        val response = client.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty response")
        if (!response.isSuccessful) throw IOException("Gemini error ${response.code}: $responseBody")

        val json = Json.parseToJsonElement(responseBody).jsonObject
        val candidates = json["candidates"]?.jsonArray ?: buildJsonArray { }
        if (candidates.isEmpty()) return AiChatResult(text = "")

        val parts = candidates[0].jsonObject["content"]?.jsonObject?.get("parts")?.jsonArray ?: buildJsonArray { }
        val text = parts.joinToString("") { it.jsonObject["text"]?.jsonPrimitive?.content ?: "" }.trim()

        return AiChatResult(text = text, usage = parseUsage(json["usageMetadata"]?.jsonObject, config.model))
    }

    companion object {
        fun formatReferences(references: List<Map<String, String>>): String {
            if (references.isEmpty()) return "无明确依据。"
            return references.mapIndexed { index, ref ->
                "[${index + 1}] ${ref["title"] ?: ""}\n${ref["content"] ?: ""}"
            }.joinToString("\n\n")
        }

        fun parseUsage(raw: JsonObject?, model: String): AiUsage? {
            if (raw == null) return null
            val prompt = intValue(raw, "prompt_tokens", "prompt_eval_count", "input_tokens", "promptTokenCount")
            val completion = intValue(raw, "completion_tokens", "eval_count", "output_tokens", "candidatesTokenCount")
            val total = intValue(raw, "total_tokens", "totalTokenCount").let { if (it > 0) it else prompt + completion }
            if (prompt == 0 && completion == 0 && total == 0) return null

            val cacheHit = intValue(raw, "prompt_cache_hit_tokens", "cache_read_input_tokens", "cachedContentTokenCount")
            val explicitMiss = intValue(raw, "prompt_cache_miss_tokens")
            val cacheMiss = if (explicitMiss > 0) explicitMiss else maxOf(0, prompt - cacheHit)
            val ratio = if (cacheHit + cacheMiss > 0 && cacheHit > 0)
                Math.round(cacheHit.toDouble() / (cacheHit + cacheMiss) * 10000.0) / 10000.0 else null

            val costUsd = estimateCostUsd(model, cacheHit, cacheMiss, completion)
            return AiUsage(
                promptTokens = prompt,
                completionTokens = completion,
                totalTokens = total,
                promptCacheHitTokens = cacheHit,
                promptCacheMissTokens = cacheMiss,
                cacheHitRatio = ratio,
                costUsd = costUsd,
                costCny = costUsd?.let { Math.round(it * USD_TO_CNY * 1_000_000.0) / 1_000_000.0 }
            )
        }

        private fun intValue(obj: JsonObject, vararg keys: String): Int {
            for (key in keys) {
                val value = obj[key]?.jsonPrimitive?.content ?: continue
                try {
                    return value.toDouble().toInt()
                } catch (_: NumberFormatException) { continue }
            }
            return 0
        }

        private fun estimateCostUsd(model: String, cacheHit: Int, cacheMiss: Int, completion: Int): Double? {
            val pricing = MODEL_PRICING_USD_PER_1M[model] ?: return null
            val cost = cacheHit * pricing["cache_hit"]!! +
                       cacheMiss * pricing["cache_miss"]!! +
                       completion * pricing["output"]!!
            return Math.round(cost / 1_000_000 * 1_000_000.0) / 1_000_000.0
        }
    }
}
