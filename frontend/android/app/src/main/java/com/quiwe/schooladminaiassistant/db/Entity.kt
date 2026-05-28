package com.quiwe.schooladminaiassistant.db

import androidx.room.*

@Entity(tableName = "knowledge_files")
data class KnowledgeFileEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "filename") val filename: String,
    @ColumnInfo(name = "category", defaultValue = "其他") val category: String = "其他",
    @ColumnInfo(name = "parsed_text", defaultValue = "") val parsedText: String = "",
    @ColumnInfo(name = "upload_time") val uploadTime: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "chunk_count", defaultValue = "0") val chunkCount: Int = 0,
    @ColumnInfo(name = "status", defaultValue = "indexed") val status: String = "indexed"
)

@Entity(
    tableName = "knowledge_chunks",
    foreignKeys = [ForeignKey(
        entity = KnowledgeFileEntity::class,
        parentColumns = ["id"],
        childColumns = ["file_id"],
        onDelete = ForeignKey.CASCADE
    )],
    indices = [Index("file_id")]
)
data class KnowledgeChunkEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "file_id") val fileId: Long,
    @ColumnInfo(name = "chunk_text") val chunkText: String,
    @ColumnInfo(name = "chunk_index", defaultValue = "0") val chunkIndex: Int = 0,
    @ColumnInfo(name = "embedding_id") val embeddingId: String? = null
)

@Entity(tableName = "faq_items")
data class FaqItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "question") val question: String,
    @ColumnInfo(name = "answer") val answer: String,
    @ColumnInfo(name = "category", defaultValue = "其他") val category: String = "其他",
    @ColumnInfo(name = "allow_auto_reply", defaultValue = "1") val allowAutoReply: Boolean = true,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
    @ColumnInfo(name = "updated_at") val updatedAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "reply_history")
data class ReplyHistoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "student_question") val studentQuestion: String,
    @ColumnInfo(name = "ai_answer") val aiAnswer: String,
    @ColumnInfo(name = "final_answer") val finalAnswer: String,
    @ColumnInfo(name = "category", defaultValue = "其他") val category: String = "其他",
    @ColumnInfo(name = "confidence", defaultValue = "0.0") val confidence: Double = 0.0,
    @ColumnInfo(name = "need_human_review", defaultValue = "0") val needHumanReview: Boolean = false,
    @ColumnInfo(name = "cost_cny") val costCny: Double? = null,
    @ColumnInfo(name = "cost_usd") val costUsd: Double? = null,
    @ColumnInfo(name = "created_at") val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "settings")
data class SettingEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "key", index = true) val key: String,
    @ColumnInfo(name = "value", defaultValue = "") val value: String = ""
)
