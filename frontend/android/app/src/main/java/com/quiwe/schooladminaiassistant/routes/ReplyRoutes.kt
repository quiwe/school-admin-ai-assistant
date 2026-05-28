package com.quiwe.schooladminaiassistant.routes

import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import com.quiwe.schooladminaiassistant.services.*
import kotlinx.serialization.json.Json

class ReplyRoutes(
    private val replyService: ReplyService,
    private val historyDao: HistoryDao
) {
    suspend fun generate(body: String): String {
        val req = apiJson.decodeFromString<GenerateReplyRequest>(body)
        val res = replyService.generateReply(req.question, req.style)
        return apiJson.encodeToString(ReplyResponse.serializer(), res)
    }

    suspend fun rewrite(body: String): String {
        val req = apiJson.decodeFromString<RewriteRequest>(body)
        val res = replyService.rewriteReply(req.question, req.answer, req.style)
        return apiJson.encodeToString(RewriteResponse.serializer(), res)
    }
}

class StudentRoutes(
    private val replyService: ReplyService,
    private val historyDao: HistoryDao
) {
    suspend fun generateReply(body: String, accessKey: String): String {
        val req = apiJson.decodeFromString<StudentReplyRequest>(body)
        val full = replyService.generateReply(req.question, req.style)
        // Save to history
        try {
            historyDao.insert(
                ReplyHistoryEntity(
                    studentQuestion = req.question,
                    aiAnswer = full.answer,
                    finalAnswer = full.answer,
                    category = full.category,
                    confidence = full.confidence,
                    needHumanReview = full.needHumanReview,
                    costCny = full.costCny,
                    costUsd = full.costUsd
                )
            )
        } catch (_: Exception) { }
        val res = StudentReplyResponse(
            answer = full.answer,
            category = full.category,
            needHumanReview = full.needHumanReview
        )
        return apiJson.encodeToString(StudentReplyResponse.serializer(), res)
    }
}
