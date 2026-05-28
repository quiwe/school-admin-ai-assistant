package com.quiwe.schooladminaiassistant.db

import androidx.room.*

@Dao
interface KnowledgeDao {
    @Insert
    suspend fun insertFile(file: KnowledgeFileEntity): Long

    @Update
    suspend fun updateFile(file: KnowledgeFileEntity)

    @Query("SELECT * FROM knowledge_files ORDER BY upload_time DESC")
    suspend fun listFiles(): List<KnowledgeFileEntity>

    @Query("SELECT * FROM knowledge_files WHERE category = :category ORDER BY upload_time DESC")
    suspend fun listFilesByCategory(category: String): List<KnowledgeFileEntity>

    @Query("SELECT * FROM knowledge_files WHERE id = :id")
    suspend fun getFile(id: Long): KnowledgeFileEntity?

    @Delete
    suspend fun deleteFile(file: KnowledgeFileEntity)

    @Query("DELETE FROM knowledge_chunks WHERE file_id = :fileId")
    suspend fun deleteChunksByFileId(fileId: Long)

    @Insert
    suspend fun insertChunks(chunks: List<KnowledgeChunkEntity>)

    @Query("SELECT * FROM knowledge_chunks")
    suspend fun getAllChunks(): List<KnowledgeChunkEntity>

    @Query("SELECT * FROM knowledge_chunks WHERE file_id = :fileId ORDER BY chunk_index")
    suspend fun getChunksByFileId(fileId: Long): List<KnowledgeChunkEntity>

    @Query("SELECT COUNT(*) FROM knowledge_chunks WHERE file_id = :fileId")
    suspend fun chunkCount(fileId: Long): Int
}

@Dao
interface FaqDao {
    @Insert
    suspend fun insert(faq: FaqItemEntity): Long

    @Update
    suspend fun update(faq: FaqItemEntity)

    @Query("SELECT * FROM faq_items ORDER BY updated_at DESC")
    suspend fun listAll(): List<FaqItemEntity>

    @Query("SELECT * FROM faq_items WHERE id = :id")
    suspend fun getById(id: Long): FaqItemEntity?

    @Delete
    suspend fun delete(faq: FaqItemEntity)

    @Query("SELECT * FROM faq_items WHERE allow_auto_reply = 1")
    suspend fun listAutoReply(): List<FaqItemEntity>

    @Query("SELECT * FROM faq_items WHERE question LIKE '%' || :keyword || '%' OR answer LIKE '%' || :keyword || '%' ORDER BY updated_at DESC")
    suspend fun search(keyword: String): List<FaqItemEntity>

    @Query("SELECT * FROM faq_items WHERE category = :category ORDER BY updated_at DESC")
    suspend fun listByCategory(category: String): List<FaqItemEntity>

    @Query("DELETE FROM faq_items")
    suspend fun deleteAll()
}

@Dao
interface HistoryDao {
    @Insert
    suspend fun insert(history: ReplyHistoryEntity): Long

    @Query("SELECT * FROM reply_history ORDER BY created_at DESC LIMIT :limit")
    suspend fun listRecent(limit: Int = 200): List<ReplyHistoryEntity>

    @Query("SELECT * FROM reply_history WHERE student_question LIKE '%' || :keyword || '%' OR final_answer LIKE '%' || :keyword || '%' ORDER BY created_at DESC LIMIT :limit")
    suspend fun search(keyword: String, limit: Int = 200): List<ReplyHistoryEntity>

    @Query("SELECT * FROM reply_history WHERE category = :category ORDER BY created_at DESC LIMIT :limit")
    suspend fun listByCategory(category: String, limit: Int = 200): List<ReplyHistoryEntity>

    @Query("SELECT * FROM reply_history WHERE student_question LIKE '%' || :keyword || '%' OR final_answer LIKE '%' || :keyword || '%'")
    suspend fun searchAll(keyword: String): List<ReplyHistoryEntity>

    @Query("DELETE FROM reply_history WHERE id IN (:ids)")
    suspend fun deleteByIds(ids: List<Long>): Int

    @Delete
    suspend fun delete(history: ReplyHistoryEntity)
}

@Dao
interface SettingDao {
    @Query("SELECT * FROM settings WHERE `key` = :key LIMIT 1")
    suspend fun getByKey(key: String): SettingEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(setting: SettingEntity)

    @Query("SELECT * FROM settings")
    suspend fun listAll(): List<SettingEntity>

    @Query("DELETE FROM settings WHERE `key` = :key")
    suspend fun deleteByKey(key: String)
}
