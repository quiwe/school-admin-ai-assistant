package com.quiwe.schooladminaiassistant

import android.content.Context
import com.quiwe.schooladminaiassistant.db.*
import com.quiwe.schooladminaiassistant.models.*
import com.quiwe.schooladminaiassistant.routes.*
import com.quiwe.schooladminaiassistant.services.*
import fi.iki.elonen.NanoHTTPD
import kotlinx.coroutines.*
import java.io.ByteArrayInputStream
import java.io.File
import java.io.FileInputStream
import java.io.InputStream
import java.net.URLDecoder
import kotlin.text.Charsets

class AppServer(
    port: Int,
    private val context: Context
) : NanoHTTPD(port) {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val db = AppDatabase.getInstance(context)
    private val aiProviderService = AiProviderService()
    private val replyService = ReplyService(
        aiProviderService, db.knowledgeDao(), db.faqDao(), db.historyDao(), db.settingDao()
    )
    private val replyRoutes = ReplyRoutes(replyService, db.historyDao())
    private val studentRoutes = StudentRoutes(replyService, db.historyDao())
    private val knowledgeRoutes = KnowledgeRoutes(db.knowledgeDao(), db.faqDao(), context)
    private val faqRoutes = FaqRoutes(db.faqDao(), db.knowledgeDao(), context)
    private val historyRoutes = HistoryRoutes(db.historyDao())
    private val settingsRoutes = SettingsRoutes(db.settingDao(), aiProviderService)
    private val dataRoutes = DataRoutes(db.knowledgeDao(), db.faqDao(), db.historyDao(), db.settingDao())
    private val appRoutes = AppRoutes()

    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri.trimEnd('/')
        val method = session.method

        // Handle CORS preflight
        if (method == Method.OPTIONS) {
            return corsResponse()
        }

        val response = try {
            runBlocking(scope.coroutineContext) {
                route(session, uri, method)
            }
        } catch (e: Exception) {
            jsonError(e.message ?: "Server error", 500)
        }

        return addCors(response)
    }

    private fun addCors(response: Response): Response {
        response.addHeader("Access-Control-Allow-Origin", "*")
        response.addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
        response.addHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Access-Key, X-Student-Access-Key")
        response.addHeader("Access-Control-Allow-Credentials", "true")
        return response
    }

    private fun corsResponse(): Response {
        val response = newFixedLengthResponse(Response.Status.OK, "text/plain", "")
        return addCors(response)
    }

    private suspend fun route(session: IHTTPSession, uri: String, method: Method): Response {
        // Parse body
        val body = parseBody(session)
        val files = parseFiles(session)

        return when {
            // Health
            uri == "/api/health" && method == Method.GET ->
                json(appRoutes.health())

            // App info
            uri == "/api/app/info" && method == Method.GET ->
                json(appRoutes.appInfo())
            uri == "/api/app/student-link" && method == Method.GET ->
                json(appRoutes.studentLink())
            uri == "/api/app/admin-link" && method == Method.GET ->
                json(appRoutes.adminLink())
            uri == "/api/app/update/check" && method == Method.GET ->
                json(appRoutes.updateCheck())
            uri == "/api/app/update/progress" && method == Method.GET ->
                json(appRoutes.updateProgress())

            // Reply
            uri == "/api/reply/generate" && method == Method.POST ->
                json(replyRoutes.generate(body))
            uri == "/api/reply/rewrite" && method == Method.POST ->
                json(replyRoutes.rewrite(body))

            // Student
            uri == "/api/student/reply/generate" && method == Method.POST -> {
                val accessKey = session.headers["x-student-access-key"]
                    ?: session.parms["access_key"] ?: ""
                json(studentRoutes.generateReply(body, accessKey))
            }

            // Knowledge
            uri == "/api/knowledge/upload" && method == Method.POST -> {
                val filePath = files["file"]
                val filename = session.parms["filename"] ?: files["filename"]
                val category = session.parms["category"] ?: "其他"
                val importFaq = session.parms["import_faq"]?.equals("true", true) ?: false
                json(knowledgeRoutes.upload(body, filePath, filename, category, importFaq))
            }
            uri == "/api/knowledge/list" && method == Method.GET -> {
                val category = session.parms["category"]
                json(knowledgeRoutes.list(category))
            }
            uri.startsWith("/api/knowledge/") && uri.endsWith("/reindex") && method == Method.POST -> {
                val fileId = extractId(uri, "/api/knowledge/", "/reindex")
                if (fileId < 0) jsonError("Invalid id", 400)
                else json(knowledgeRoutes.reindex(fileId))
            }
            uri.startsWith("/api/knowledge/") && method == Method.DELETE -> {
                val fileId = extractId(uri, "/api/knowledge/", null)
                if (fileId < 0) jsonError("Invalid id", 400)
                else json(knowledgeRoutes.delete(fileId))
            }
            uri.startsWith("/api/knowledge/") && method == Method.PATCH -> {
                val fileId = extractId(uri, "/api/knowledge/", null)
                if (fileId < 0) jsonError("Invalid id", 400)
                else json(knowledgeRoutes.update(fileId, body))
            }

            // FAQ
            uri == "/api/faq/create" && method == Method.POST ->
                json(faqRoutes.create(body))
            uri == "/api/faq/list" && method == Method.GET -> {
                val keyword = session.parms["keyword"]
                json(faqRoutes.list(keyword))
            }
            uri == "/api/faq/similar" && method == Method.GET -> {
                val question = session.parms["question"] ?: ""
                val excludeId = session.parms["exclude_id"]?.toLongOrNull()
                json(faqRoutes.similar(question, excludeId))
            }
            uri == "/api/faq/import" && method == Method.POST -> {
                val filePath = files["file"]
                json(faqRoutes.import(filePath))
            }
            uri == "/api/faq/export" && method == Method.GET -> {
                val keyword = session.parms["keyword"]
                val (bytes, filename) = faqRoutes.export(keyword)
                fileResponse(bytes, filename, "text/csv; charset=utf-8")
            }
            uri.startsWith("/api/faq/") && method == Method.PUT -> {
                val id = extractId(uri, "/api/faq/", null)
                if (id < 0) jsonError("Invalid id", 400)
                else json(faqRoutes.update(id, body))
            }
            uri.startsWith("/api/faq/") && method == Method.DELETE -> {
                val id = extractId(uri, "/api/faq/", null)
                if (id < 0) jsonError("Invalid id", 400)
                else json(faqRoutes.delete(id))
            }

            // History
            uri == "/api/history/list" && method == Method.GET -> {
                val keyword = session.parms["keyword"]
                val category = session.parms["category"]
                json(historyRoutes.list(keyword, category))
            }
            uri == "/api/history/create" && method == Method.POST ->
                json(historyRoutes.create(body))
            uri == "/api/history/delete" && method == Method.POST ->
                json(historyRoutes.deleteMany(body))
            uri.startsWith("/api/history/") && method == Method.DELETE -> {
                val id = extractId(uri, "/api/history/", null)
                if (id < 0) jsonError("Invalid id", 400)
                else json(historyRoutes.deleteOne(id))
            }

            // Settings
            uri == "/api/settings/ai" && method == Method.GET ->
                json(settingsRoutes.getAISettings())
            uri == "/api/settings/ai" && method == Method.PUT ->
                json(settingsRoutes.updateAISettings(body))
            uri == "/api/settings/ai/models" && method == Method.POST ->
                json(settingsRoutes.listModels(body))
            uri == "/api/settings/ai/test" && method == Method.POST ->
                json(settingsRoutes.testProvider(body))
            uri == "/api/settings/qq" && method == Method.GET ->
                json(settingsRoutes.getQQSettings())
            uri == "/api/settings/wecom" && method == Method.GET ->
                json(settingsRoutes.getWeComSettings())
            uri == "/api/settings/cost-stats" && method == Method.GET ->
                json(settingsRoutes.getCostStats())
            uri == "/api/settings/budget" && method == Method.PUT ->
                json(settingsRoutes.updateBudget(body))
            uri == "/api/settings/autostart" && method == Method.GET ->
                json(settingsRoutes.getAutoStart())

            // Data
            uri == "/api/data/export" && method == Method.GET -> {
                val (bytes, filename) = dataRoutes.exportData()
                fileResponse(bytes, filename, "application/json; charset=utf-8")
            }
            uri == "/api/data/import" && method == Method.POST ->
                json(dataRoutes.importData(body))

            // Static files (frontend)
            else -> serveStatic(uri)
        }
    }

    private fun serveStatic(uri: String): Response {
        val path = if (uri == "/" || uri.isEmpty()) "/index.html" else uri
        val assetPath = "public${path}"

        // Try frontend dist (from assets)
        val assetStream = try {
            context.assets.open(assetPath)
        } catch (_: Exception) {
            null
        }

        if (assetStream != null) {
            val mime = mimeType(path)
            return newChunkedResponse(Response.Status.OK, mime, assetStream)
        }

        // Fallback to index.html for SPA routing
        val indexStream = try {
            context.assets.open("public/index.html")
        } catch (_: Exception) {
            null
        }

        if (indexStream != null) {
            return newChunkedResponse(Response.Status.OK, "text/html", indexStream)
        }

        return jsonError("Not found", 404)
    }

    private fun parseBody(session: IHTTPSession): String {
        val files = HashMap<String, String>()
        try {
            session.parseBody(files)
        } catch (_: Exception) { }
        return files["postData"] ?: ""
    }

    private fun parseFiles(session: IHTTPSession): Map<String, String> {
        val files = HashMap<String, String>()
        try {
            session.parseBody(files)
        } catch (_: Exception) { }
        // Return temp file paths for uploaded files
        val result = mutableMapOf<String, String>()
        for ((key, value) in files) {
            if (key != "postData") result[key] = value
        }
        // Also check parms for file content
        val body = files["postData"] ?: ""
        if (body.isNotBlank() && body.startsWith("--")) {
            // Multipart body already parsed by NanoHTTPD
        }
        return result
    }

    private fun extractId(uri: String, prefix: String, suffix: String?): Long {
        val start = prefix.length
        val end = if (suffix != null) uri.indexOf(suffix) else uri.length
        if (end < 0) return -1
        return uri.substring(start, end).toLongOrNull() ?: -1
    }

    private fun json(content: String): Response {
        return newFixedLengthResponse(
            Response.Status.OK,
            "application/json",
            content
        )
    }

    private fun jsonError(message: String, status: Int): Response {
        val body = """{"detail":"${message.replace("\"", "\\\"")}"}"""
        return newFixedLengthResponse(
            Response.Status.lookup(status),
            "application/json",
            body
        )
    }

    private fun fileResponse(bytes: ByteArray, filename: String, mime: String): Response {
        val response = newFixedLengthResponse(Response.Status.OK, mime, ByteArrayInputStream(bytes), bytes.size.toLong())
        response.addHeader("Content-Disposition", "attachment; filename=\"$filename\"")
        return response
    }

    private fun mimeType(path: String): String = when {
        path.endsWith(".html") -> "text/html"
        path.endsWith(".css") -> "text/css"
        path.endsWith(".js") -> "application/javascript"
        path.endsWith(".json") -> "application/json"
        path.endsWith(".png") -> "image/png"
        path.endsWith(".jpg") || path.endsWith(".jpeg") -> "image/jpeg"
        path.endsWith(".svg") -> "image/svg+xml"
        path.endsWith(".ico") -> "image/x-icon"
        path.endsWith(".woff2") -> "font/woff2"
        path.endsWith(".woff") -> "font/woff"
        else -> "application/octet-stream"
    }
}
