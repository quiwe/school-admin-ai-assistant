package com.quiwe.schooladminaiassistant.services

import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

data class RetrievedReference(
    val title: String,
    val content: String,
    val score: Double,
    val sourceType: String
)

object RagService {
    private val TOKEN_RE = Regex("[a-zA-Z0-9_]+|[\\u4e00-\\u9fff]+")
    private val NOISE_WORD_RE = Regex(
        "(?:xmlformats\\.org|schemaRefs|datastoreItem|WordDocument|MsoDataStore|Microsoft Office Word)",
        RegexOption.IGNORE_CASE
    )

    fun chunkText(text: String, chunkSize: Int = 700, overlap: Int = 120): List<String> {
        val clean = text.replace(Regex("\n{3,}"), "\n\n").trim()
        if (clean.isEmpty()) return emptyList()
        val chunks = mutableListOf<String>()
        var start = 0
        while (start < clean.length) {
            val end = min(start + chunkSize, clean.length)
            chunks.add(clean.substring(start, end).trim())
            if (end == clean.length) break
            start = max(end - overlap, start + 1)
        }
        return chunks.filter { it.isNotEmpty() }
    }

    fun tokenize(text: String): List<String> {
        val tokens = mutableListOf<String>()
        for (match in TOKEN_RE.findAll(text.lowercase())) {
            val token = match.value
            if (hasCJK(token)) {
                tokens.addAll(cjkNgrams(token))
            } else {
                tokens.add(token)
            }
        }
        return tokens
    }

    private fun hasCJK(text: String): Boolean = text.any { it in '\u4e00'..'\u9fff' }

    private fun cjkNgrams(text: String): List<String> {
        if (text.length <= 2) return listOf(text)
        val tokens = mutableListOf<String>()
        for (size in listOf(2, 3, 4)) {
            if (text.length < size) continue
            for (i in 0..text.length - size) {
                tokens.add(text.substring(i, i + size))
            }
        }
        return tokens
    }

    fun bm25Score(query: String, document: String): Double {
        val qTerms = tokenize(query)
        val dTerms = tokenize(document)
        if (qTerms.isEmpty() || dTerms.isEmpty()) return 0.0
        val docLen = dTerms.size
        val frequencies = dTerms.groupingBy { it }.eachCount()
        var score = 0.0
        for (term in qTerms.toSet()) {
            val tf = frequencies[term] ?: 0
            if (tf > 0) {
                score += (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * docLen / 120.0))
            }
        }
        return score / sqrt(max(qTerms.toSet().size.toDouble(), 1.0))
    }

    fun similarityScore(query: String, document: String): Double {
        val bm25 = bm25Score(query, document)
        val qTerms = tokenize(query).toSet()
        val dTerms = tokenize(document).toSet()
        if (qTerms.isEmpty() || dTerms.isEmpty()) return bm25

        val overlap = (qTerms intersect dTerms).size
        val overlapScore = overlap / sqrt(max(qTerms.size.toDouble(), 1.0))
        val compactQuery = compactText(query)
        val compactDoc = compactText(document)
        var substringBonus = 0.0
        if (compactQuery.isNotEmpty() && compactDoc.contains(compactQuery)) {
            substringBonus = min(1.2, compactQuery.length / 10.0)
        } else if (compactDoc.isNotEmpty() && compactDoc.length <= 40 && compactQuery.contains(compactDoc)) {
            substringBonus = min(1.0, compactDoc.length / 12.0)
        }
        return max(bm25, overlapScore * 2.4 + substringBonus)
    }

    private fun compactText(text: String): String =
        TOKEN_RE.findAll(text.lowercase()).map { it.value }.joinToString("")

    fun retrieveReferences(
        faqs: List<com.quiwe.schooladminaiassistant.db.FaqItemEntity>,
        chunks: List<Pair<com.quiwe.schooladminaiassistant.db.KnowledgeChunkEntity, String>>,
        question: String,
        limit: Int = 5
    ): List<RetrievedReference> {
        val candidates = mutableListOf<RetrievedReference>()

        for (faq in faqs) {
            if (!faq.allowAutoReply) continue
            val score = max(
                similarityScore(question, faq.question) * 1.35,
                similarityScore(question, "${faq.question}\n${faq.answer}")
            )
            if (score > 0.12) {
                candidates.add(
                    RetrievedReference(
                        title = "FAQ：${faq.question.take(40)}",
                        content = "问：${faq.question}\n答：${faq.answer}",
                        score = score + 0.35,
                        sourceType = "faq"
                    )
                )
            }
        }

        for ((chunk, filename) in chunks) {
            val score = similarityScore(question, chunk.chunkText)
            if (score > 0.12) {
                candidates.add(
                    RetrievedReference(
                        title = filename,
                        content = cleanReferenceText(chunk.chunkText),
                        score = score,
                        sourceType = "knowledge"
                    )
                )
            }
        }

        candidates.sortByDescending { it.score }
        if (candidates.isEmpty()) return emptyList()
        val cutoff = max(0.12, candidates.first().score * 0.3)
        return candidates.filter { it.score >= cutoff }.take(limit)
    }

    fun cleanReferenceText(text: String): String {
        var result = NOISE_WORD_RE.replace(text, " ")
        result = result.map { if (isReferenceChar(it)) it else ' ' }.joinToString("")
        result = Regex("[ \\t]{2,}").replace(result, " ")
        result = Regex("\n{3,}").replace(result, "\n\n")
        val lines = result.lines().map { it.trim() }.filter { hasEnoughReadable(it) }
        return lines.joinToString("\n").ifEmpty { text.trim() }
    }

    private fun isReferenceChar(c: Char): Boolean = when {
        c in "\r\n\t " -> true
        c.isISOControl() -> false
        c.code <= 127 -> c.isLetterOrDigit() || c in ".,;:!?()-_=+[]{}|/\\@#\$%^&*'\"<>`~ "
        c in '\u4e00'..'\u9fff' -> true
        c in '\u3000'..'\u303f' -> true
        c in '\uff00'..'\uffef' -> true
        else -> false
    }

    private fun hasEnoughReadable(line: String): Boolean {
        val readable = line.count { it.isLetterOrDigit() || it in '\u4e00'..'\u9fff' }
        return readable >= 4 && readable / max(line.length.toDouble(), 1.0) >= 0.35
    }

    fun confidenceFromReferences(refs: List<RetrievedReference>): Double {
        if (refs.isEmpty()) return 0.0
        val top = refs.first().score
        return Math.round((min(0.92, 0.42 + top / 3.5 + min(refs.size, 5) * 0.04)) * 100.0) / 100.0
    }
}
