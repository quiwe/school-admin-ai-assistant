package com.quiwe.schooladminaiassistant.services

import android.content.Context
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.text.PDFTextStripper
import java.io.*
import java.nio.charset.Charset
import java.util.zip.ZipFile

object FileParser {
    private val CONTROL_CHARS = Regex("[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F]")
    private val XML_NOISE = Regex(
        "(?:xmlformats\\.org|schemaRefs|datastoreItem|WordDocument|MsoDataStore|Microsoft Office Word|mc:Ignorable|w:rsid\\w+)",
        RegexOption.IGNORE_CASE
    )

    const val MAX_UPLOAD_BYTES = 20L * 1024 * 1024 // 20 MB
    private const val MAX_ZIP_UNCOMPRESSED_BYTES = 200L * 1024 * 1024 // 200 MB
    private const val MAX_PDF_PAGES = 200
    private const val MAX_SHEET_ROWS = 5000
    private const val MAX_TXT_BYTES = 10L * 1024 * 1024 // 10 MB

    fun init(context: Context) {
        PDFBoxResourceLoader.init(context)
    }

    fun validateFileSize(path: String) {
        val size = File(path).length()
        if (size > MAX_UPLOAD_BYTES) {
            throw IOException("文件过大，请上传不超过 20MB 的文件。")
        }
    }

    private fun checkZipSafety(path: String) {
        ZipFile(path).use { zip ->
            var total = 0L
            for (entry in zip.entries()) {
                total += entry.size
                if (total > MAX_ZIP_UNCOMPRESSED_BYTES) {
                    throw IOException("文件解压后体积过大，请检查后重新上传。")
                }
            }
        }
    }

    fun parseFile(context: Context, filePath: String, originalName: String? = null): String {
        val typeName = originalName?.ifBlank { null } ?: filePath
        return when {
            typeName.endsWith(".pdf", true) -> cleanParsedText(parsePdf(filePath))
            typeName.endsWith(".docx", true) -> cleanParsedText(parseDocx(filePath))
            typeName.endsWith(".pptx", true) -> cleanParsedText(parsePptx(filePath))
            typeName.endsWith(".xlsx", true) -> cleanParsedText(parseXlsx(filePath))
            typeName.endsWith(".xls", true) -> throw IOException("旧版 .xls 格式在手机端暂不支持解析，请转换为 .xlsx 后上传。")
            typeName.endsWith(".txt", true) -> cleanParsedText(parseTxt(filePath))
            typeName.endsWith(".doc", true) -> throw IOException("旧版 .doc 格式在手机端暂不支持解析，请转换为 .docx 后上传。")
            typeName.endsWith(".ppt", true) -> throw IOException("旧版 .ppt 格式在手机端暂不支持解析，请转换为 .pptx 后上传。")
            else -> throw IOException("不支持的文件格式")
        }
    }

    private fun parsePdf(path: String): String {
        PDDocument.load(File(path)).use { doc ->
            if (doc.numberOfPages > MAX_PDF_PAGES) {
                throw IOException("PDF 页数过多（超过 $MAX_PDF_PAGES 页），请拆分后上传。")
            }
            val stripper = PDFTextStripper()
            return stripper.getText(doc).trim()
        }
    }

    private fun parseDocx(path: String): String {
        checkZipSafety(path)
        return extractDocxXmlText(path)
    }

    private fun parsePptx(path: String): String {
        checkZipSafety(path)
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
        val textNodes = Regex("<(?:[A-Za-z0-9]+:)?t(?:\\s[^>]*)?>(.*?)</(?:[A-Za-z0-9]+:)?t>", RegexOption.DOT_MATCHES_ALL)
            .findAll(xml)
            .map { decodeXmlEntities(it.groupValues[1]) }
            .filter { it.isNotBlank() }
            .toList()
        if (textNodes.isNotEmpty()) return textNodes.joinToString(" ")

        return decodeXmlEntities(xml.replace(Regex("<[^>]+>"), " "))
            .replace(Regex("\\s{2,}"), " ")
            .trim()
    }

    private fun decodeXmlEntities(text: String): String {
        return text
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&apos;", "'")
            .replace(Regex("&#(\\d+);")) { match ->
                match.groupValues[1].toIntOrNull()?.toChar()?.toString() ?: ""
            }
    }

    private fun parseXlsx(path: String): String {
        checkZipSafety(path)
        val sb = StringBuilder()
        ZipFile(path).use { zip ->
            val sharedStrings = mutableListOf<String>()
            val ssEntry = zip.getEntry("xl/sharedStrings.xml")
            if (ssEntry != null) {
                zip.getInputStream(ssEntry).use { stream ->
                    val xmlText = stream.bufferedReader().readText()
                    val siRegex = Regex("<si[^>]*>.*?</si>", RegexOption.DOT_MATCHES_ALL)
                    for (match in siRegex.findAll(xmlText)) {
                        sharedStrings.add(extractTextFromXml(match.value))
                    }
                }
            }

            for (entry in zip.entries()) {
                if (entry.name.matches(Regex("xl/worksheets/sheet\\d+\\.xml"))) {
                    zip.getInputStream(entry).use { stream ->
                        val xmlText = stream.bufferedReader().readText()
                        val rowRegex = Regex("<row[^>]*>.*?</row>", RegexOption.DOT_MATCHES_ALL)
                        val cellRegex = Regex("<c[^>]*>.*?</c>", RegexOption.DOT_MATCHES_ALL)
                        var rowCount = 0
                        for (rowMatch in rowRegex.findAll(xmlText)) {
                            if (rowCount >= MAX_SHEET_ROWS) {
                                sb.append("（行数过多，已截断）\n")
                                break
                            }
                            val rowText = rowMatch.value
                            val cells = cellRegex.findAll(rowText).mapNotNull { cellMatch ->
                                val cell = cellMatch.value
                                val cellText = when {
                                    Regex("t=\"s\"").containsMatchIn(cell) -> {
                                        val vMatch = Regex("<v>(\\d+)</v>").find(cell)
                                        val idx = vMatch?.groupValues?.get(1)?.toIntOrNull()
                                        if (idx != null && idx < sharedStrings.size) sharedStrings[idx] else ""
                                    }
                                    Regex("t=\"inlineStr\"").containsMatchIn(cell) -> extractTextFromXml(cell)
                                    else -> {
                                        val vMatch = Regex("<v>(.*?)</v>", RegexOption.DOT_MATCHES_ALL).find(cell)
                                        val rawValue = vMatch?.groupValues?.get(1)?.trim() ?: ""
                                        if (rawValue.isNotBlank()) decodeXmlEntities(rawValue) else extractTextFromXml(cell)
                                    }
                                }
                                cellText.takeIf { it.isNotBlank() }
                            }
                            if (cells.any()) {
                                sb.append(cells.joinToString("\t"))
                                sb.append("\n")
                            }
                            rowCount++
                        }
                    }
                }
            }
        }
        return sb.toString().trim()
    }

    private fun parseTxt(path: String): String {
        val file = File(path)
        if (file.length() > MAX_TXT_BYTES) {
            throw IOException("TXT 文件过大，请上传不超过 10MB 的文件。")
        }
        val bytes = file.readBytes()
        val utf8 = bytes.toString(Charsets.UTF_8).trim()
        if (!looksMojibake(utf8)) return utf8
        return bytes.toString(Charset.forName("GBK")).trim()
    }

    private fun cleanParsedText(text: String): String {
        return XML_NOISE.replace(CONTROL_CHARS.replace(text, ""), " ")
            .replace(Regex("[ \\t]{2,}"), " ")
            .replace(Regex("\\n{3,}"), "\n\n")
            .lines()
            .map { it.trim() }
            .filter { it.isNotBlank() && readableRatio(it) >= 0.25 }
            .joinToString("\n")
            .trim()
    }

    private fun readableRatio(text: String): Double {
        if (text.isBlank()) return 0.0
        val readable = text.count { it.isLetterOrDigit() || it in '\u4e00'..'\u9fff' || it in "，。！？；：、（）《》-_/ " }
        return readable.toDouble() / text.length
    }

    private fun looksMojibake(text: String): Boolean {
        val bad = text.count { it == '\uFFFD' || it == '锟' || it == '烫' || it == '屯' }
        return bad >= 2 || bad.toDouble() / maxOf(text.length, 1) > 0.02
    }

    fun extractFaqRowsFromSpreadsheet(context: Context, path: String, originalName: String? = null): List<Map<String, String>> {
        val typeName = originalName?.ifBlank { null } ?: path
        if (!typeName.endsWith(".xlsx", true) && !typeName.endsWith(".xls", true)) return emptyList()
        if (typeName.endsWith(".xls", true)) return emptyList()

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
