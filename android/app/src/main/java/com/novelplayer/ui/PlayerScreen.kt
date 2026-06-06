package com.novelplayer.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.novelplayer.data.NovelRepository
import com.novelplayer.data.SentenceData
import com.novelplayer.player.AudioPlayer
import com.novelplayer.player.PlayerState
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PlayerScreen(
    novelId: Int,
    chapterId: Int,
    onBack: () -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val repository = remember { NovelRepository(context) }
    val audioPlayer = remember { AudioPlayer(context) }
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    var sentences by remember { mutableStateOf<List<SentenceData>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var downloadProgress by remember { mutableStateOf<Map<Int, Float>>(emptyMap()) }
    var isDownloading by remember { mutableStateOf(false) }
    val playerState by audioPlayer.state.collectAsState()

    // Load sentences
    LaunchedEffect(novelId, chapterId) {
        isLoading = true
        repository.getSentences(novelId, chapterId).fold(
            onSuccess = { sentences = it },
            onFailure = {
                error = it.message ?: "Failed to load sentences"
            }
        )
        isLoading = false
    }

    // Auto-scroll to current sentence
    LaunchedEffect(playerState.currentSentenceIndex) {
        val index = playerState.currentSentenceIndex
        if (index >= 0 && index < sentences.size) {
            listState.animateScrollToItem(index)
        }
    }

    // Download all audio
    fun downloadAll() {
        scope.launch {
            isDownloading = true
            for (i in sentences.indices) {
                val sentence = sentences[i]
                if (sentence.audioUrl == null) continue
                downloadProgress = downloadProgress + (i to 0f)
                repository.downloadAudio(novelId, chapterId, sentence) { progress ->
                    downloadProgress = downloadProgress + (i to progress)
                }
                downloadProgress = downloadProgress + (i to 1f)
            }
            isDownloading = false
        }
    }

    // Prepare player when sentences load
    LaunchedEffect(sentences) {
        if (sentences.isNotEmpty()) {
            val urls = sentences.mapNotNull { s ->
                if (s.audioUrl != null) {
                    ApiClient.getBaseUrl().trimEnd('/') + s.audioUrl
                } else null
            }
            if (urls.isNotEmpty()) {
                audioPlayer.prepare(urls)
            }
        }
    }

    DisposableEffect(Unit) {
        onDispose { audioPlayer.release() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("第${chapterId}章") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
                },
                actions = {
                    if (isDownloading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp).padding(end = 8.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        IconButton(onClick = { downloadAll() }) {
                            Icon(Icons.Default.Download, contentDescription = "下载")
                        }
                    }
                }
            )
        },
        bottomBar = {
            PlayerControlBar(
                playerState = playerState,
                totalSentences = sentences.size,
                onPlayPause = { audioPlayer.playPause() },
                onNext = { audioPlayer.playNext() },
                onPrev = {
                    val idx = playerState.currentSentenceIndex
                    if (idx > 0) audioPlayer.seekToSentence(idx - 1)
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                error != null -> {
                    Text(
                        error!!,
                        modifier = Modifier.align(Alignment.Center).padding(16.dp),
                        color = MaterialTheme.colorScheme.error
                    )
                }
                else -> {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                        contentPadding = PaddingValues(vertical = 8.dp, bottom = 80.dp)
                    ) {
                        itemsIndexed(sentences) { index, sentence ->
                            val isCurrent = index == playerState.currentSentenceIndex
                            val hasAudio = sentence.audioUrl != null
                            val progress = downloadProgress[index]

                            SentenceItem(
                                index = index,
                                sentence = sentence,
                                isCurrent = isCurrent,
                                hasAudio = hasAudio,
                                downloadProgress = progress,
                                onClick = {
                                    if (hasAudio && !isDownloading) {
                                        audioPlayer.seekToSentence(index)
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SentenceItem(
    index: Int,
    sentence: SentenceData,
    isCurrent: Boolean,
    hasAudio: Boolean,
    downloadProgress: Float?,
    onClick: () -> Unit
) {
    val bgColor = if (isCurrent) MaterialTheme.colorScheme.primaryContainer
    else Color.Transparent

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp)
            .clip(MaterialTheme.shapes.small)
            .background(bgColor)
            .clickable(enabled = hasAudio, onClick = onClick)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Sentence number
        Surface(
            shape = CircleShape,
            color = if (hasAudio) MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)
            else MaterialTheme.colorScheme.surfaceVariant
        ) {
            Text(
                text = "${index + 1}",
                modifier = Modifier.padding(6.dp),
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(Modifier.width(8.dp))

        // Sentence text
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = sentence.text,
                fontSize = 16.sp,
                fontWeight = if (isCurrent) FontWeight.Bold else FontWeight.Normal,
                lineHeight = 24.sp
            )
            if (sentence.speaker != null || sentence.emotion != null) {
                Row {
                    sentence.speaker?.let {
                        Text(it, fontSize = 11.sp, color = MaterialTheme.colorScheme.primary)
                    }
                    if (sentence.speaker != null && sentence.emotion != null) {
                        Text(" · ", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    sentence.emotion?.let {
                        Text(it, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }

        // Download progress indicator
        if (downloadProgress != null && downloadProgress < 1f) {
            CircularProgressIndicator(
                modifier = Modifier.size(16.dp),
                strokeWidth = 2.dp
            )
        } else if (hasAudio) {
            Icon(
                Icons.Default.PlayArrow,
                contentDescription = "播放",
                modifier = Modifier.size(20.dp),
                tint = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
fun PlayerControlBar(
    playerState: PlayerState,
    totalSentences: Int,
    onPlayPause: () -> Unit,
    onNext: () -> Unit,
    onPrev: () -> Unit
) {
    Surface(
        tonalElevation = 4.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 24.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            IconButton(onClick = onPrev) {
                Icon(Icons.Default.SkipPrevious, contentDescription = "上一句", modifier = Modifier.size(32.dp))
            }

            Spacer(Modifier.width(16.dp))

            FilledIconButton(
                onClick = onPlayPause,
                modifier = Modifier.size(56.dp)
            ) {
                Icon(
                    if (playerState.isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                    contentDescription = if (playerState.isPlaying) "暂停" else "播放",
                    modifier = Modifier.size(32.dp)
                )
            }

            Spacer(Modifier.width(16.dp))

            IconButton(onClick = onNext) {
                Icon(Icons.Default.SkipNext, contentDescription = "下一句", modifier = Modifier.size(32.dp))
            }
        }
    }
}
