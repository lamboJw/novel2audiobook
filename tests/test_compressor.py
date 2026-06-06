import pytest
import subprocess
import tempfile
import os
from src.audio.compressor import AudioCompressor


def test_ffmpeg_available():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    assert result.returncode == 0


def test_compress_wav_to_opus():
    compressor = AudioCompressor()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    opus_path = wav_path.replace(".wav", ".opus")

    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-ar", "24000", "-ac", "1", wav_path
        ], check=True, capture_output=True)

        compressor.compress(wav_path, opus_path)
        assert os.path.exists(opus_path)
        assert os.path.getsize(opus_path) < os.path.getsize(wav_path)
    finally:
        for p in [wav_path, opus_path]:
            if os.path.exists(p):
                os.unlink(p)
