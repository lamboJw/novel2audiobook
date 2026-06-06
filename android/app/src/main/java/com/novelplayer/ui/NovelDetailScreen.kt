package com.novelplayer.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.HourglassEmpty
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.novelplayer.data.ApiClient
import com.novelplayer.data.ChapterInfo
import com.novelplayer.data.NovelDetail
import com.novelplayer.data.NovelRepository
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NovelDetailScreen(
    novelId: Int,
    onChapterClick: (Int) -> Unit,
    onBack: () -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val repository = remember { NovelRepository(context) }
    val scope = rememberCoroutineScope()

    var novel by remember { mutableStateOf<NovelDetail?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(novelId) {
        isLoading = true
        repository.getNovel(novelId).fold(
            onSuccess = { novel = it },
            onFailure = { error = it.message }
        )
        isLoading = false
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(novel?.title ?: "加载中...") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "返回")
                    }
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
                novel != null -> {
                    LazyColumn(modifier = Modifier.fillMaxSize()) {
                        item {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text("作者: ${novel!!.author}", fontSize = 14.sp)
                                Spacer(Modifier.height(4.dp))
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text("状态: ", fontSize = 14.sp)
                                    StatusBadge(novel!!.status)
                                }
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    "共 ${novel!!.chapters.size} 章",
                                    fontSize = 14.sp,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Spacer(Modifier.height(12.dp))
                                HorizontalDivider()
                                Spacer(Modifier.height(8.dp))
                                Text("章节列表", fontWeight = FontWeight.Bold)
                            }
                        }
                        items(novel!!.chapters) { chapter ->
                            ChapterCard(
                                chapter = chapter,
                                onClick = {
                                    if (chapter.status == "done") {
                                        onChapterClick(chapter.id)
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
fun ChapterCard(chapter: ChapterInfo, onClick: () -> Unit) {
    val isPlayable = chapter.status == "done"

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 3.dp)
            .clickable(enabled = isPlayable, onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isPlayable) 1.dp else 0.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isPlayable)
                MaterialTheme.colorScheme.surface
            else
                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            if (isPlayable) {
                Icon(
                    Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp)
                )
            } else {
                Icon(
                    Icons.Default.HourglassEmpty,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(20.dp)
                )
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    "第${chapter.index}章 ${chapter.title}",
                    fontWeight = if (isPlayable) FontWeight.Medium else FontWeight.Normal
                )
                Text(
                    "${chapter.sentenceCount} 句",
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (!isPlayable) {
                StatusBadge(chapter.status)
            }
        }
    }
}
