package com.quiwe.schooladminaiassistant.services

import android.content.Context
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import java.io.*
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import java.util.zip.ZipInputStream
import javax.xml.parsers.DocumentBuilderFactory

object FileParser {
    private val XML_FACTORY = DocumentBuilderFactory.newInstance()

    fun init(context: Context) {
        PDFBoxResourceLoader.init(context)
    }

    fun parseFile(context: Context, filePath: String): String {
        return when {
            filePath.endsWith(".pdf", true) -> parsePdf(filePath)
            filePath.endsWith(".docx", true) -> parseDocx(filePath)
            filePath.endsWith(".pptx", true) -> parsePptx(filePath)
            filePath.endsWith(".xlsx", true) -> parseXlsx(filePath)
            filePath.endsWith(".xls", true) -> parseXlsText(filePath)
            filePath.endsWith(".txt", true) -> parseTxt(filePath)
            filePath.endsWith(".doc", true) -> "旧版 .doc 格式在手机端暂不支持解析，请转换为 .docx 后上传。"
            filePath.endsWith(".ppt", true) -> "旧版 .ppt 格式在手机端暂不支持解析，请转换为 .pptx 后上传。"
            else -> throw IOException("不支持的文件格式")
        }
    }

    private fun parsePdf(path: String): String {
        PDDocument.load(File(path)).use { doc ->
            val stripper = PDFTextStripper()
            return stripper.getText(doc).trim()
        }
    }

    private fun parseDocx(path: String): String {
        return extractDocxXmlText(path)
    }

    private fun parsePptx(path: String): String {
        val sb = StringBuilder()
        ZipFile(path).use { zip ->
            for (entry in zip.entries()) {
                if (entry.name.matches(Regex("ppt/slides/slide\\d+\\.xml"))) {
                    zip.getInputStream(entry).use { stream ->
                        val xmlText = stream.bufferedReader().readText()
                        sb.append(extractTextFromXml(xmlText))
                        sb.append("\n\n")
                    }
                }
            }
        }
        return sb.toString().trim()
    }

    private fun extractDocxXmlText(path: String): String {
        ZipFile(path).use { zip ->
            val entry = zip.getEntry("word/document.xml") ?: throw IOException("Invalid DOCX: no word/document.xml")
            zip.getInputStream(entry).use { stream ->
                val xmlText = stream.bufferedReader().readText()
                return extractTextFromXml(xmlText)
            }
        }
    }

    private fun extractTextFromXml(xml: String): String {
        // Simple tag-stripping approach for robustness
        val sb = StringBuilder()
        var inTag = false
        var inText = false
        for (i in xml.indices) {
            when {
                xml[i] == '<' -> { inTag = true; inText = false }
                xml[i] == '>' -> { inTag = false; inText = false }
                !inTag -> {
                    if (xml[i] !in "\r\n" || sb.isNotEmpty()) {
                        sb.append(xml[i])
                    }
                    inText = true
                }
            }
        }
        return sb.toString()
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&apos;", "'")
            .replace(Regex("\\s{2,}"), " ")
            .trim()
    }

    private fun parseXlsx(path: String): String {
        val sb = StringBuilder()
        ZipFile(path).use { zip ->
            val sharedStrings = mutableListOf<String>()
            val ssEntry = zip.getEntry("xl/sharedStrings.xml")
            if (ssEntry != null) {
                zip.getInputStream(ssEntry).use { stream ->
                    val xmlText = stream.bufferedReader().readText()
                    val siRegex = Regex("<si[^>]*>.*?</si>")
                    for (match in siRegex.findAll(xmlText)) {
                        sharedStrings.add(extractTextFromXml(match.value))
                    }
                }
            }

            for (entry in zip.entries()) {
                if (entry.name.matches(Regex("xl/worksheets/sheet\\d+\\.xml"))) {
                    zip.getInputStream(entry).use { stream ->
                        val xmlText = stream.bufferedReader().readText()
                        val rowRegex = Regex("<row[^>]*>.*?</row>")
                        for (rowMatch in rowRegex.findAll(xmlText)) {
                            val rowText = rowMatch.value
                            val cellRegex = Regex("<c[^>]*>.*?</c>")
                            val cells = cellRegex.findAll(rowText).map { cellMatch ->
                                val cell = cellMatch.value
                                val tMatch = Regex("t=\"s\"").find(cell)
                                if (tMatch != null) {
                                    val vMatch = Regex("<v>(\\d+)</v>").find(cell)
                                    val idx = vMatch?.groupValues?.get(1)?.toIntOrNull()
                                    if (idx != null && idx < sharedStrings.size) {
                                        sharedStrings[idx]
                                    } else ""
                                } else {
                                    extractTextFromXml(cell)
                                }
                            }.filter { it.isNotBlank() }
                            if (cells.any()) {
                                sb.append(cells.joinToString("\t"))
                                sb.append("\n")
                            }
                        }
                    }
                }
            }
        }
        return sb.toString().trim()
    }

    private fun parseXlsText(path: String): String {
        // Old .xls: try basic text extraction via BiffView-ish approach
        // For Android v1, return a note
        return "旧版 .xls 格式在手机端暂不支持完整解析，请转换为 .xlsx 后上传。建议用 WPS 或 Excel 另存为 .xlsx。"
    }

    private fun parseTxt(path: String): String {
        return File(path).readText(Charsets.UTF_8).trim()
    }

    fun extractFaqRowsFromSpreadsheet(context: Context, path: String): List<Map<String, String>> {
        if (!path.endsWith(".xlsx", true) && !path.endsWith(".xls", true)) return emptyList()
        if (path.endsWith(".xls", true)) return emptyList()

        val rows = mutableListOf<Map<String, String>>()
        val allText = parseXlsx(path)
        val lines = allText.lines().filter { it.isNotBlank() }
        if (lines.size < 2) return emptyList()

        val header = lines[0].split("\t").map { it.trim() }
        val qIdx = header.indexOfFirst { it.contains("问题") || it.equals("question", true) }
        val aIdx = header.indexOfFirst { it.contains("答案") || it.contains("回复") || it.equals("answer", true) }
        val cIdx = header.indexOfFirst { it.contains("分类") || it.equals("category", true) }

        if (qIdx < 0 || aIdx < 0) return emptyList()

        for (i in 1 until lines.size) {
            val cells = lines[i].split("\t").map { it.trim() }
            if (cells.size <= maxOf(qIdx, aIdx)) continue
            val q = cells[qIdx]
            val a = cells[aIdx]
            if (q.isBlank() || a.isBlank()) continue
            rows.add(
                mapOf(
                    "question" to q,
                    "answer" to a,
                    "category" to (if (cIdx >= 0 && cIdx < cells.size) cells[cIdx] else "其他")
                )
            )
        }
        return rows
    }
}
