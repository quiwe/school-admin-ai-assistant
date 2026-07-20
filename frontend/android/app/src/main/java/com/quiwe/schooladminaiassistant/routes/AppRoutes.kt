package com.quiwe.schooladminaiassistant.routes

import com.quiwe.schooladminaiassistant.models.*

class AppRoutes {
    fun health(): String = """{"status":"ok"}"""

    fun appInfo(): String {
        val res = AppInfoResponse(
            name = "高校行政AI回复助手",
            version = "1.0.0-android",
            developer = "",
            latestUpdate = "Android 独立版首次发布"
        )
        return apiJson.encodeToString(AppInfoResponse.serializer(), res)
    }

    fun studentLink(): String {
        val res = StudentLinkResponse(url = "安卓端无需学生链接，直接使用即可。")
        return apiJson.encodeToString(StudentLinkResponse.serializer(), res)
    }

    fun adminLink(): String {
        val res = AdminLinkResponse(
            url = "http://localhost:8765",
            apiBase = ""
        )
        return apiJson.encodeToString(AdminLinkResponse.serializer(), res)
    }

    fun updateCheck(): String {
        val res = UpdateCheckResponse(
            currentVersion = "1.0.0-android",
            hasUpdate = false
        )
        return apiJson.encodeToString(UpdateCheckResponse.serializer(), res)
    }

    fun updateInstall(): String {
        return """{"ok":false,"message":"安卓端暂不支持应用内安装更新。请从发布页下载安装新版 APK。","installer_path":null}"""
    }

    fun updateProgress(): String {
        val res = UpdateProgressResponse(status = "idle")
        return apiJson.encodeToString(UpdateProgressResponse.serializer(), res)
    }
}
