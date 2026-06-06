package com.novelplayer.data

import com.novelplayer.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface ApiService {

    @GET("api/novels")
    suspend fun listNovels(): List<NovelSummary>

    @GET("api/novels/{id}")
    suspend fun getNovel(@Path("id") id: Int): NovelDetail

    @DELETE("api/novels/{id}")
    suspend fun deleteNovel(@Path("id") id: Int): Map<String, String>

    @GET("api/novels/{novelId}/characters")
    suspend fun getCharacters(@Path("novelId") novelId: Int): List<CharacterData>

    @GET("api/novels/{novelId}/chapters/{chapterId}/sentences")
    suspend fun getSentences(
        @Path("novelId") novelId: Int,
        @Path("chapterId") chapterId: Int
    ): List<SentenceData>

    @GET("api/audio/{novelId}/{chapterId}/{sentenceSeq}")
    suspend fun getAudioUrl(
        @Path("novelId") novelId: Int,
        @Path("chapterId") chapterId: Int,
        @Path("sentenceSeq") sentenceSeq: String
    ): okhttp3.ResponseBody
}

object ApiClient {
    private var baseUrl: String = BuildConfig.DEFAULT_SERVER_URL

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private var retrofit: Retrofit = buildRetrofit()

    private fun buildRetrofit(): Retrofit {
        return Retrofit.Builder()
            .baseUrl(if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/")
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    val service: ApiService get() = retrofit.create(ApiService::class.java)

    fun updateBaseUrl(newUrl: String) {
        baseUrl = newUrl
        retrofit = buildRetrofit()
    }

    fun getBaseUrl(): String = baseUrl
}
