package com.novelplayer.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.novelplayer.data.ApiClient
import com.novelplayer.data.NovelSummary
import com.novelplayer.data.NovelRepository
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NovelListScreen(onNovelClick: (Int) -> Unit) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val repository = remember { NovelRepository(context) }
    val scope = rememberCoroutineScope()

    var novels by remember { mutableStateOf<List<NovelSummary>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var showSettings by remember { mutableStateOf(false) }
    var serverUrl by remember { mutableStateOf(ApiClient.getBaseUrl()) }

    fun loadNovels() {
        scope.launch {
            isLoading = true
            error = null
            repository.listNovels().fold(
                onSuccess = { novels = it },
                onFailure = { error = it.message ?: "Failed to load novels" }
            )
            isLoading = false
        }
    }

    LaunchedEffect(Unit) { loadNovels() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("有声小说", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { loadNovels() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新")
                    }
                    IconButton(onClick = { showSettings = true }) {
                        Icon(Icons.Default.Settings, contentDescription = "设置")
                    }
                }
            )
        }
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                isLoading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                error != null -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center).padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(error!!, color = MaterialTheme.colorScheme.error)
                        Spacer(Modifier.height(8.dp))
                        Button(onClick = { loadNovels() }) { Text("重试") }
                    }
                }
                novels.isEmpty() -> {
                    Text(
                        "暂无小说\n请先在 Web 端导入小说",
                        modifier = Modifier.align(Alignment.Center),
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
                else -> {
                    LazyColumn(modifier = Modifier.fillMaxSize()) {
                        items(novels) { novel ->
                            NovelCard(novel = novel, onClick = { onNovelClick(novel.id) })
                        }
                    }
                }
            }
        }
    }

    if (showSettings) {
        AlertDialog(
            onDismissRequest = { showSettings = false },
            title = { Text("服务器设置") },
            text = {
                Column {
                    OutlinedTextField(
                        value = serverUrl,
                        onValueChange = { serverUrl = it },
                        label = { Text("服务器地址") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "默认为 ${ApiClient.getBaseUrl()}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    ApiClient.updateBaseUrl(serverUrl)
                    showSettings = false
                    loadNovels()
                }) { Text("保存") }
            },
            dismissButton = {
                TextButton(onClick = { showSettings = false }) { Text("取消") }
            }
        )
    }
}

@Composable
fun NovelCard(novel: NovelSummary, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp)
            .clickable(onClick = onClick),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(novel.title, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                if (novel.author.isNotBlank()) {
                    Text(novel.author, fontSize = 14.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    StatusBadge(novel.status)
                    Spacer(Modifier.width(8.dp))
                    Text(novel.fileType, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
fun StatusBadge(status: String) {
    val color = when (status) {
        "done" -> MaterialTheme.colorScheme.primary
        "error" -> MaterialTheme.colorScheme.error
        else -> MaterialTheme.colorScheme.tertiary
    }
    Surface(
        color = color.copy(alpha = 0.15f),
        shape = MaterialTheme.shapes.small
    ) {
        Text(
            text = status,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
            fontSize = 12.sp,
            color = color
        )
    }
}
