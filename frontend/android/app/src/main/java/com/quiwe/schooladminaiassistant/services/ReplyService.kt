package com.quiwe.schooladminaiassistant.services

import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*

class ReplyService(
    private val aiProvider: AiProviderService,
    private val knowledgeDao: KnowledgeDao,
    private val faqDao: FaqDao,
    private val historyDao: HistoryDao,
    private val settingDao: SettingDao
) {
    suspend fun generateReply(question: String, style: String): ReplyResponse {
        val category = ClassifierService.classify(question)
        val (sensitive, _) = SafetyService.detect(question)

        // RAG retrieval
        val faqs = faqDao.listAutoReply()
        val allChunks = knowledgeDao.getAllChunks()
        val chunkPairs = allChunks.map { chunk ->
            val file = knowledgeDao.getFile(chunk.fileId)
            chunk to (file?.filename ?: "知识库文件")
        }
        val references = RagService.retrieveReferences(faqs, chunkPairs, question)
        val confidence = RagService.confidenceFromReferences(references)
        val hasReliable = references.isNotEmpty() && confidence >= 0.45

        val responseRefs = references.map { Reference(title = it.title, content = it.content.take(500)) }

        if (sensitive) {
            return ReplyResponse(
                answer = SafetyService.HUMAN_REVIEW_TEMPLATE,
                category = category,
                confidence = confidence,
                needHumanReview = true,
                references = responseRefs,
                aiUsed = false
            )
        }

        if (!hasReliable) {
            return ReplyResponse(
                answer = "同学你好，这个问题目前在已有知识库中没有找到明确依据，需要进一步核实后再回复。请先补充姓名、学号、专业及相关截图或材料，老师确认具体情况后再给你准确答复。",
                category = category,
                confidence = confidence,
                needHumanReview = true,
                references = responseRefs,
                aiUsed = false
            )
        }

        val config = loadAiConfig()
        val refsForAi = references.map { mapOf("title" to it.title, "content" to it.content.take(800)) }

        return try {
            val result = aiProvider.generateReply(question, refsForAi, style, config)
            val answer = result.text.trim().ifEmpty { throw RuntimeException("大模型返回了空内容。") }
            ReplyResponse(
                answer = answer,
                category = category,
                confidence = confidence,
                needHumanReview = false,
                references = responseRefs,
                aiUsed = true,
                aiProvider = config.aiProvider,
                aiModel = config.model,
                promptTokens = result.usage?.promptTokens,
                completionTokens = result.usage?.completionTokens,
                totalTokens = result.usage?.totalTokens,
                promptCacheHitTokens = result.usage?.promptCacheHitTokens,
                promptCacheMissTokens = result.usage?.promptCacheMissTokens,
                cacheHitRatio = result.usage?.cacheHitRatio,
                costUsd = result.usage?.costUsd,
                costCny = result.usage?.costCny
            )
        } catch (e: Exception) {
            ReplyResponse(
                answer = "已检索到知识库依据，但当前大模型调用失败，暂时不能生成可发送回复。请到系统设置检查 API Key、Base URL 和模型名称，确认模型连接正常后再生成。",
                category = category,
                confidence = confidence,
                needHumanReview = true,
                references = responseRefs,
                aiUsed = false,
                aiProvider = config.aiProvider,
                aiModel = config.model,
                aiError = safeErrorMessage(e)
            )
        }
    }

    suspend fun rewriteReply(question: String, answer: String, style: String): RewriteResponse {
        return try {
            val config = loadAiConfig()
            val result = aiProvider.rewriteReply(question, answer, style, config)
            RewriteResponse(
                answer = result.text.trim(),
                aiUsed = true,
                promptTokens = result.usage?.promptTokens,
                completionTokens = result.usage?.completionTokens,
                totalTokens = result.usage?.totalTokens,
                promptCacheHitTokens = result.usage?.promptCacheHitTokens,
                promptCacheMissTokens = result.usage?.promptCacheMissTokens,
                cacheHitRatio = result.usage?.cacheHitRatio,
                costUsd = result.usage?.costUsd,
                costCny = result.usage?.costCny
            )
        } catch (_: Exception) {
            val local = localRewrite(answer, style)
            RewriteResponse(answer = local.trim(), aiUsed = false)
        }
    }

    suspend fun loadAiConfig(): AiConfig {
        val providerId = normalizeProviderId(
            settingDao.getByKey("ai_provider")?.value
        )
        val preset = PROVIDER_MAP[providerId]!!

        val apiKey = settingDao.getByKey(providerSettingKey(providerId, "api_key"))?.value
        val baseUrl = settingDao.getByKey(providerSettingKey(providerId, "base_url"))?.value
            ?: preset.defaultBaseUrl
        val model = settingDao.getByKey(providerSettingKey(providerId, "model"))?.value
            ?: preset.defaultModel

        return AiConfig(
            aiProvider = providerId,
            providerType = preset.providerType,
            apiKey = apiKey,
            model = model,
            baseUrl = baseUrl
        )
    }

    companion object {
        fun safeErrorMessage(e: Exception): String {
            val msg = (e.message ?: "未知错误")
                .replace(Regex("sk-[A-Za-z0-9_-]{6,}"), "sk-***")
                .replace(Regex("([A-Za-z0-9_-]{4})[A-Za-z0-9_-]{12,}"), "$1***")
            return msg.take(500)
        }

        fun localRewrite(answer: String, style: String): String = when (style) {
            "shorter" -> answer.take(140) + if (answer.length > 140) "..." else ""
            "formal" -> answer.replace("你好", "您好")
            "warmer" -> "同学你好，请先不用着急。" + answer.removePrefix("同学你好，")
            else -> answer
        }
    }
}
