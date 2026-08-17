package com.quiwe.schooladminaiassistant.routes

import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import com.quiwe.schooladminaiassistant.services.RagService
import kotlinx.serialization.json.*

class DataRoutes(
    private val knowledgeDao: KnowledgeDao,
    private val faqDao: FaqDao,
    private val historyDao: HistoryDao,
    private val settingDao: SettingDao
) {
    suspend fun exportData(): Pair<ByteArray, String> {
        val faqs = faqDao.listAll()
        val files = knowledgeDao.listFiles()
        val history = historyDao.listRecent(10000)
        val settings = settingDao.listAll().filter {
            !it.key.contains("api_key") && !it.key.contains("secret")
        }

        val json = buildJsonObject {
            put("format", "school-admin-ai-assistant-backup")
            put("version", 1)
            put("exported_at", java.time.Instant.now().toString())
            putJsonArray("faq_items") {
                for (faq in faqs) {
                    addJsonObject {
                        put("question", faq.question)
                        put("answer", faq.answer)
                        put("category", faq.category)
                        put("allow_auto_reply", faq.allowAutoReply)
                    }
                }
            }
            putJsonArray("knowledge_files") {
                for (file in files) {
                    addJsonObject {
                        put("filename", file.filename)
                        put("category", file.category)
                        put("parsed_text", file.parsedText)
                    }
                }
            }
            putJsonArray("reply_history") {
                for (h in history) {
                    addJsonObject {
                        put("student_question", h.studentQuestion)
                        put("ai_answer", h.aiAnswer)
                        put("final_answer", h.finalAnswer)
                        put("category", h.category)
                        put("confidence", h.confidence)
                        put("need_human_review", h.needHumanReview)
                    }
                }
            }
            putJsonArray("settings") {
                for (s in settings) {
                    addJsonObject {
                        put("key", s.key)
                        put("value", s.value)
                    }
                }
            }
        }
        val jsonStr = Json { prettyPrint = true }.encodeToString(JsonElement.serializer(), json)
        return jsonStr.toByteArray(Charsets.UTF_8) to "backup.json"
    }

    suspend fun importData(body: String): String {
        val json = Json.parseToJsonElement(body).jsonObject
        val format = json["format"]?.jsonPrimitive?.contentOrNull
        if (format != null && format != "school-admin-ai-assistant-backup") {
            return """{"detail":"备份文件格式不匹配。"}"""
        }
        var importedFaq = 0
        var skippedFaq = 0
        var importedKnowledge = 0
        var importedHistory = 0

        val existingQuestions = faqDao.listAll().map { it.question }.toMutableList()
        json["faq_items"]?.jsonArray?.forEach { item ->
            val q = item.jsonObject["question"]?.jsonPrimitive?.content ?: return@forEach
            val a = item.jsonObject["answer"]?.jsonPrimitive?.content ?: return@forEach
            val cat = item.jsonObject["category"]?.jsonPrimitive?.content ?: "其他"
            val auto = item.jsonObject["allow_auto_reply"]?.jsonPrimitive?.booleanOrNull ?: true

            val dup = existingQuestions.any { RagService.similarityScore(q, it) > 0.85 }
            if (dup) { skippedFaq++; return@forEach }
            faqDao.insert(FaqItemEntity(question = q, answer = a, category = cat, allowAutoReply = auto))
            existingQuestions.add(q)
            importedFaq++
        }

        json["knowledge_files"]?.jsonArray?.forEach { item ->
            val fname = item.jsonObject["filename"]?.jsonPrimitive?.content ?: return@forEach
            val text = item.jsonObject["parsed_text"]?.jsonPrimitive?.content ?: ""
            val cat = item.jsonObject["category"]?.jsonPrimitive?.content ?: "其他"
            val chunks = RagService.chunkText(text)
            val fileId = knowledgeDao.insertFile(
                KnowledgeFileEntity(
                    filename = fname, category = cat, parsedText = text,
                    chunkCount = chunks.size, status = if (chunks.isNotEmpty()) "indexed" else "empty"
                )
            )
            if (chunks.isNotEmpty()) {
                knowledgeDao.insertChunks(chunks.mapIndexed { i, t -> KnowledgeChunkEntity(fileId = fileId, chunkText = t, chunkIndex = i) })
            }
            importedKnowledge++
        }

        json["reply_history"]?.jsonArray?.forEach { item ->
            val obj = item.jsonObject
            historyDao.insert(
                ReplyHistoryEntity(
                    studentQuestion = obj["student_question"]?.jsonPrimitive?.content ?: "",
                    aiAnswer = obj["ai_answer"]?.jsonPrimitive?.content ?: "",
                    finalAnswer = obj["final_answer"]?.jsonPrimitive?.content ?: "",
                    category = obj["category"]?.jsonPrimitive?.content ?: "其他",
                    confidence = obj["confidence"]?.jsonPrimitive?.doubleOrNull ?: 0.0,
                    needHumanReview = obj["need_human_review"]?.jsonPrimitive?.booleanOrNull ?: false
                )
            )
            importedHistory++
        }

        json["settings"]?.jsonArray?.forEach { item ->
            val obj = item.jsonObject
            val key = obj["key"]?.jsonPrimitive?.content ?: return@forEach
            val value = obj["value"]?.jsonPrimitive?.content ?: ""
            if (!key.contains("api_key") && !key.contains("secret")) {
                settingDao.upsert(SettingEntity(key = key, value = value))
            }
        }

        val res = BackupImportResponse(
            ok = true,
            importedFaq = importedFaq,
            skippedFaqDuplicates = skippedFaq,
            importedKnowledgeFiles = importedKnowledge,
            importedHistory = importedHistory
        )
        return apiJson.encodeToString(BackupImportResponse.serializer(), res)
    }
}
