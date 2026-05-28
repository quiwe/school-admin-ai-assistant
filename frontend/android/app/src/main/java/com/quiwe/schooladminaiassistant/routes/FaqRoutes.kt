package com.quiwe.schooladminaiassistant.routes

import android.content.Context
import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import com.quiwe.schooladminaiassistant.services.FileParser
import com.quiwe.schooladminaiassistant.services.RagService
import kotlinx.serialization.builtins.ListSerializer
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class FaqRoutes(
    private val faqDao: FaqDao,
    private val knowledgeDao: KnowledgeDao,
    private val context: Context
) {
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())

    suspend fun create(body: String): String {
        val req = apiJson.decodeFromString<FaqCreateRequest>(body)
        if (!req.force) {
            val existing = faqDao.listAll()
            for (faq in existing) {
                val score = RagService.similarityScore(req.question, faq.question)
                if (score > 0.75) {
                    return """{"detail":"检测到与 FAQ「${faq.question.take(30)}」高度相似的问题（相似度 ${(score * 100).toInt()}%）。如确认不是重复问题，请勾选「强制添加」。"}"""
                }
            }
        }
        val now = System.currentTimeMillis()
        val entity = FaqItemEntity(
            question = req.question,
            answer = req.answer,
            category = req.category,
            allowAutoReply = req.allowAutoReply,
            createdAt = now,
            updatedAt = now
        )
        val id = faqDao.insert(entity)
        val created = faqDao.getById(id)!!
        return apiJson.encodeToString(FaqItemResponse.serializer(), toResponse(created))
    }

    suspend fun list(keyword: String?): String {
        val items = if (keyword.isNullOrBlank()) faqDao.listAll() else faqDao.search(keyword)
        return apiJson.encodeToString(ListSerializer(FaqItemResponse.serializer()), items.map { toResponse(it) })
    }

    suspend fun similar(question: String, excludeId: Long?): String {
        val items = faqDao.listAll().filter { it.id != excludeId }
        val scored = items.map { item ->
            val score = RagService.similarityScore(question, item.question)
            item to score
        }.filter { it.second > 0.1 }
            .sortedByDescending { it.second }
            .take(5)
        val result = scored.map { toResponse(it.first) }
        return apiJson.encodeToString(ListSerializer(FaqItemResponse.serializer()), result)
    }

    suspend fun export(keyword: String?): Pair<ByteArray, String> {
        val items = if (keyword.isNullOrBlank()) faqDao.listAll() else faqDao.search(keyword)
        val csv = buildString {
            append("问题,答案,分类,允许自动回复,创建时间,更新时间\n")
            for (item in items) {
                append("\"${item.question.replace("\"", "\"\"")}\",")
                append("\"${item.answer.replace("\"", "\"\"")}\",")
                append("${item.category},")
                append("${if (item.allowAutoReply) "是" else "否"},")
                append("${dateFormat.format(Date(item.createdAt))},")
                append("${dateFormat.format(Date(item.updatedAt))}\n")
            }
        }
        return csv.toByteArray(Charsets.UTF_8) to "faq_export.csv"
    }

    suspend fun import(filePath: String?): String {
        if (filePath == null) return """{"detail":"未提供文件"}"""
        val rows = FileParser.extractFaqRowsFromSpreadsheet(context, filePath)
        if (rows.isEmpty()) return """{"detail":"未能从文件中提取到 FAQ 数据，请确保第一行为表头且包含「问题」「答案」列。"}"""
        var imported = 0
        var skipped = 0
        for (row in rows) {
            val q = row["question"] ?: continue
            val a = row["answer"] ?: continue
            val existing = faqDao.listAll()
            val tooSimilar = existing.any { RagService.similarityScore(q, it.question) > 0.85 }
            if (tooSimilar) { skipped++; continue }
            faqDao.insert(
                FaqItemEntity(
                    question = q,
                    answer = a,
                    category = row["category"] ?: "其他",
                    allowAutoReply = true
                )
            )
            imported++
        }
        val res = FaqImportResponse(imported = imported, skippedDuplicates = skipped)
        return apiJson.encodeToString(FaqImportResponse.serializer(), res)
    }

    suspend fun update(id: Long, body: String): String {
        val existing = faqDao.getById(id) ?: return """{"detail":"FAQ 不存在。"}"""
        val req = apiJson.decodeFromString<FaqUpdateRequest>(body)
        val updated = existing.copy(
            question = req.question ?: existing.question,
            answer = req.answer ?: existing.answer,
            category = req.category ?: existing.category,
            allowAutoReply = req.allowAutoReply ?: existing.allowAutoReply,
            updatedAt = System.currentTimeMillis()
        )
        faqDao.update(updated)
        val reloaded = faqDao.getById(id)!!
        return apiJson.encodeToString(FaqItemResponse.serializer(), toResponse(reloaded))
    }

    suspend fun delete(id: Long): String {
        val item = faqDao.getById(id) ?: return """{"detail":"FAQ 不存在。"}"""
        faqDao.delete(item)
        return """{"ok":true}"""
    }

    private fun toResponse(f: FaqItemEntity) = FaqItemResponse(
        id = f.id,
        question = f.question,
        answer = f.answer,
        category = f.category,
        allowAutoReply = f.allowAutoReply,
        createdAt = dateFormat.format(Date(f.createdAt)),
        updatedAt = dateFormat.format(Date(f.updatedAt))
    )
}
