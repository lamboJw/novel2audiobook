package com.novelplayer.player

import android.content.Context
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class PlayerState(
    val isPlaying: Boolean = false,
    val currentSentenceIndex: Int = -1,
    val totalSentences: Int = 0,
    val isLoading: Boolean = false,
    val error: String? = null
)

@OptIn(UnstableApi::class)
class AudioPlayer(private val context: Context) {

    private var player: ExoPlayer? = null
    private val _state = MutableStateFlow(PlayerState())
    val state: StateFlow<PlayerState> = _state.asStateFlow()

    private var audioUrls: List<String> = emptyList()
    private var currentIndex: Int = -1

    fun prepare(urls: List<String>, startIndex: Int = 0) {
        release()
        audioUrls = urls
        currentIndex = startIndex

        if (urls.isEmpty()) {
            _state.value = _state.value.copy(error = "No audio available")
            return
        }

        val player = ExoPlayer.Builder(context).build().also {
            this.player = it
        }

        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                when (playbackState) {
                    Player.STATE_READY -> {
                        _state.value = _state.value.copy(isLoading = false)
                    }
                    Player.STATE_ENDED -> {
                        playNext()
                    }
                    Player.STATE_BUFFERING -> {
                        _state.value = _state.value.copy(isLoading = true)
                    }
                }
            }

            override fun onIsPlayingChanged(isPlaying: Boolean) {
                _state.value = _state.value.copy(isPlaying = isPlaying)
            }

            override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
                _state.value = _state.value.copy(
                    error = "Playback error: ${error.message}",
                    isLoading = false
                )
            }
        })

        val mediaItems = urls.map { url ->
            MediaItem.fromUri(url)
        }

        player.setMediaItems(mediaItems, startIndex, 0)
        player.prepare()
    }

    fun play() {
        player?.play()
    }

    fun pause() {
        player?.pause()
    }

    fun playPause() {
        if (_state.value.isPlaying) pause() else play()
    }

    fun seekToSentence(index: Int) {
        if (index < 0 || index >= audioUrls.size) return
        currentIndex = index
        _state.value = _state.value.copy(currentSentenceIndex = index)
        player?.seekTo(index, 0)
        player?.play()
    }

    fun playNext() {
        val nextIndex = currentIndex + 1
        if (nextIndex < audioUrls.size) {
            seekToSentence(nextIndex)
        } else {
            // Reached end of chapter
            pause()
            _state.value = _state.value.copy(currentSentenceIndex = -1)
        }
    }

    fun getCurrentPosition(): Long {
        return player?.currentPosition ?: 0
    }

    fun getDuration(): Long {
        return player?.duration ?: 0
    }

    fun release() {
        player?.release()
        player = null
    }

    companion object {
        private const val TAG = "AudioPlayer"
    }
}
