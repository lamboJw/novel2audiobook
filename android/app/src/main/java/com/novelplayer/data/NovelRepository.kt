package com.novelplayer.data

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.net.URL

class NovelRepository(private val context: Context) {

    private val api = ApiClient.service
    private val cacheDir = File(context.cacheDir, "novel_audio")

    init {
        cacheDir.mkdirs()
    }

    suspend fun listNovels(): Result<List<NovelSummary>> = runCatching {
        api.listNovels()
    }

    suspend fun getNovel(id: Int): Result<NovelDetail> = runCatching {
        api.getNovel(id)
    }

    suspend fun deleteNovel(id: Int): Result<Unit> = runCatching {
        api.deleteNovel(id)
        deleteNovelAudioCache(id)
    }

    suspend fun getSentences(novelId: Int, chapterId: Int): Result<List<SentenceData>> = runCatching {
        api.getSentences(novelId, chapterId)
    }

    suspend fun getCharacters(novelId: Int): Result<List<CharacterData>> = runCatching {
        api.getCharacters(novelId)
    }

    suspend fun downloadAudio(
        novelId: Int,
        chapterId: Int,
        sentenceData: SentenceData,
        onProgress: (Float) -> Unit = {}
    ): Result<File> = runCatching {
        val url = sentenceData.audioUrl ?: throw IllegalArgumentException("No audio URL")
        val fileName = "novel_${novelId}_ch${chapterId}_sent${sentenceData.index}.opus"
        val file = File(cacheDir, fileName)

        if (file.exists() && file.length() > 0) {
            return@runCatching file
        }

        val fullUrl = ApiClient.getBaseUrl().trimEnd('/') + url
        val connection = URL(fullUrl).openConnection()
        connection.connect()

        val contentLength = connection.contentLengthLong
        val inputStream = connection.getInputStream()
        val outputStream = FileOutputStream(file)

        val buffer = ByteArray(8192)
        var bytesRead: Int
        var totalBytesRead = 0L

        while (inputStream.read(buffer).also { bytesRead = it } != -1) {
            outputStream.write(buffer, 0, bytesRead)
            totalBytesRead += bytesRead
            if (contentLength > 0) {
                onProgress(totalBytesRead.toFloat() / contentLength)
            }
        }

        outputStream.close()
        inputStream.close()
        file
    }

    fun getCachedAudioFile(novelId: Int, chapterId: Int, sentenceIndex: Int): File? {
        val fileName = "novel_${novelId}_ch${chapterId}_sent${sentenceIndex}.opus"
        val file = File(cacheDir, fileName)
        return if (file.exists()) file else null
    }

    fun getCacheSize(): Long {
        return cacheDir.walkTopDown().filter { it.isFile }.sumOf { it.length() }
    }

    fun clearCache() {
        cacheDir.deleteRecursively()
        cacheDir.mkdirs()
    }

    fun deleteNovelAudioCache(novelId: Int) {
        cacheDir.listFiles()?.filter {
            it.name.startsWith("novel_${novelId}_")
        }?.forEach { it.delete() }
    }
}
