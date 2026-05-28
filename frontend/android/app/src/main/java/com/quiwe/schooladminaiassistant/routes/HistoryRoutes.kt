package com.quiwe.schooladminaiassistant.routes

import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import kotlinx.serialization.builtins.ListSerializer
import java.text.SimpleDateFormat
import java.util.*

class HistoryRoutes(private val historyDao: HistoryDao) {
    private val dateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())

    suspend fun list(keyword: String?, category: String?): String {
        val items = when {
            !keyword.isNullOrBlank() && !category.isNullOrBlank() ->
                historyDao.searchByKeywordAndCategory(keyword!!, category!!)
            !keyword.isNullOrBlank() -> historyDao.search(keyword!!)
            !category.isNullOrBlank() -> historyDao.listByCategory(category!!)
            else -> historyDao.listRecent()
        }
        return apiJson.encodeToString(
            ListSerializer(HistoryItemResponse.serializer()),
            items.map { toResponse(it) }
        )
    }

    suspend fun create(body: String): String {
        val req = apiJson.decodeFromString<HistoryCreateRequest>(body)
        val entity = ReplyHistoryEntity(
            studentQuestion = req.studentQuestion,
            aiAnswer = req.aiAnswer,
            finalAnswer = req.finalAnswer,
            category = req.category,
            confidence = req.confidence,
            needHumanReview = req.needHumanReview,
            costCny = req.costCny,
            costUsd = req.costUsd
        )
        val id = historyDao.insert(entity)
        // We can't easily get the inserted entity back, return simple ok
        val res = DeleteResponse(ok = true, deleted = 1)
        return apiJson.encodeToString(DeleteResponse.serializer(), res)
    }

    suspend fun deleteMany(body: String): String {
        val req = apiJson.decodeFromString<HistoryDeleteRequest>(body)
        val deleted = historyDao.deleteByIds(req.ids)
        return apiJson.encodeToString(DeleteResponse.serializer(), DeleteResponse(ok = true, deleted = deleted))
    }

    suspend fun deleteOne(id: Long): String {
        val items = historyDao.listRecent(10000)
        val item = items.find { it.id == id }
        if (item != null) {
            historyDao.delete(item)
            return apiJson.encodeToString(DeleteResponse.serializer(), DeleteResponse(ok = true, deleted = 1))
        }
        return apiJson.encodeToString(DeleteResponse.serializer(), DeleteResponse(ok = false))
    }

    private fun toResponse(h: ReplyHistoryEntity) = HistoryItemResponse(
        id = h.id,
        studentQuestion = h.studentQuestion,
        aiAnswer = h.aiAnswer,
        finalAnswer = h.finalAnswer,
        category = h.category,
        confidence = h.confidence,
        needHumanReview = h.needHumanReview,
        costCny = h.costCny,
        costUsd = h.costUsd,
        createdAt = dateFormat.format(Date(h.createdAt))
    )
}
