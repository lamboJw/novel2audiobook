package com.novelplayer.data

import com.google.gson.annotations.SerializedName

data class NovelSummary(
    val id: Int,
    val title: String,
    val author: String,
    @SerializedName("file_type") val fileType: String,
    val status: String,
    @SerializedName("created_at") val createdAt: String
)

data class ChapterInfo(
    val id: Int,
    val index: Int,
    val title: String,
    val status: String,
    @SerializedName("sentence_count") val sentenceCount: Int
)

data class NovelDetail(
    val id: Int,
    val title: String,
    val author: String,
    val status: String,
    val chapters: List<ChapterInfo>
)

data class SentenceData(
    val index: Int,
    val text: String,
    val speaker: String?,
    val emotion: String?,
    @SerializedName("audio_url") val audioUrl: String?,
    val duration: Double?
)

data class CharacterData(
    val id: Int,
    val name: String,
    val aliases: List<String>?,
    @SerializedName("base_profile") val baseProfile: Map<String, Any>?,
    val evolution: List<Map<String, Any>>?,
    @SerializedName("voice_ref_id") val voiceRefId: Int?
)

data class CreateNovelResponse(
    val id: Int,
    val status: String
)

data class ApiMessage(
    val message: String?,
    val detail: String?
)
