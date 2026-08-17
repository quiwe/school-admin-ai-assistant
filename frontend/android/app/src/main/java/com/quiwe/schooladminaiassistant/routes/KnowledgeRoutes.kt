package com.quiwe.schooladminaiassistant.routes

import android.content.Context
import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import com.quiwe.schooladminaiassistant.services.FileParser
import com.quiwe.schooladminaiassistant.services.RagService
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.json.Json
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class KnowledgeRoutes(
    private val knowledgeDao: KnowledgeDao,
    private val faqDao: FaqDao,
    private val context: Context
) {
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())

    suspend fun upload(body: String, filePath: String?, filename: String?, category: String?, importFaq: Boolean): String {
        if (filePath == null) return """{"detail":"未提供文件"}"""
        val fname = filename ?: File(filePath).name
        val cat = category ?: "其他"
        val suffix = fname.lowercase().substringAfterLast('.', "")

        try {
            FileParser.validateFileSize(filePath)
        } catch (e: Exception) {
            return """{"detail":"${e.message}"}"""
        }

        val parsedText = try {
            FileParser.parseFile(context, filePath, fname)
        } catch (e: Exception) {
            return """{"detail":"文件解析失败：${e.message}"}"""
        }

        val chunks = RagService.chunkText(parsedText)
        val file = KnowledgeFileEntity(
            filename = fname,
            category = cat,
            parsedText = parsedText,
            chunkCount = chunks.size,
            status = if (chunks.isNotEmpty()) "indexed" else "empty",
            uploadTime = System.currentTimeMillis()
        )
        val fileId = knowledgeDao.insertFile(file)
        if (chunks.isNotEmpty()) {
            knowledgeDao.insertChunks(
                chunks.mapIndexed { index, text ->
                    KnowledgeChunkEntity(fileId = fileId, chunkText = text, chunkIndex = index)
                }
            )
        }

        if (importFaq && suffix in setOf("xlsx", "xls")) {
            for (row in FileParser.extractFaqRowsFromSpreadsheet(context, filePath, fname)) {
                faqDao.insert(
                    FaqItemEntity(
                        question = row["question"] ?: "",
                        answer = row["answer"] ?: "",
                        category = row["category"] ?: cat,
                        allowAutoReply = true
                    )
                )
            }
        }

        val created = knowledgeDao.getFile(fileId)!!
        return apiJson.encodeToString(KnowledgeFileResponse.serializer(), toResponse(created))
    }

    suspend fun list(category: String?): String {
        val files = if (category != null) knowledgeDao.listFilesByCategory(category) else knowledgeDao.listFiles()
        val list = files.map { toResponse(it) }
        return apiJson.encodeToString(ListSerializer(KnowledgeFileResponse.serializer()), list)
    }

    suspend fun delete(fileId: Long): String {
        val file = knowledgeDao.getFile(fileId) ?: return """{"detail":"知识库文件不存在。"}"""
        knowledgeDao.deleteFile(file)
        return """{"ok":true}"""
    }

    suspend fun update(fileId: Long, body: String): String {
        val req = apiJson.decodeFromString<KnowledgeUpdateRequest>(body)
        val file = knowledgeDao.getFile(fileId) ?: return """{"detail":"知识库文件不存在。"}"""
        val category = req.category?.trim() ?: ""
        if (category.isEmpty()) return """{"detail":"分类不能为空。"}"""
        knowledgeDao.updateFile(file.copy(category = category))
        val updated = knowledgeDao.getFile(fileId)!!
        return apiJson.encodeToString(KnowledgeFileResponse.serializer(), toResponse(updated))
    }

    suspend fun reindex(fileId: Long): String {
        val file = knowledgeDao.getFile(fileId) ?: return """{"detail":"知识库文件不存在。"}"""
        knowledgeDao.deleteChunksByFileId(fileId)
        val chunks = RagService.chunkText(file.parsedText)
        if (chunks.isNotEmpty()) {
            knowledgeDao.insertChunks(
                chunks.mapIndexed { index, text ->
                    KnowledgeChunkEntity(fileId = fileId, chunkText = text, chunkIndex = index)
                }
            )
        }
        knowledgeDao.updateFile(file.copy(chunkCount = chunks.size, status = if (chunks.isNotEmpty()) "indexed" else "empty"))
        val updated = knowledgeDao.getFile(fileId)!!
        return apiJson.encodeToString(KnowledgeFileResponse.serializer(), toResponse(updated))
    }

    private fun toResponse(f: KnowledgeFileEntity) = KnowledgeFileResponse(
        id = f.id,
        filename = f.filename,
        category = f.category,
        uploadTime = dateFormat.format(Date(f.uploadTime)),
        parsedText = f.parsedText,
        chunkCount = f.chunkCount,
        status = f.status
    )
}
