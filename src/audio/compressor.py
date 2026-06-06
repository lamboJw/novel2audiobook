import subprocess
import os


class AudioCompressor:
    def compress(self, wav_path: str, opus_path: str, bitrate: str = "64k"):
        os.makedirs(os.path.dirname(opus_path), exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path,
             "-c:a", "libopus", "-b:a", bitrate,
             "-vbr", "on", opus_path],
            check=True, capture_output=True
        )

    def compress_and_cleanup(self, wav_path: str, opus_path: str):
        self.compress(wav_path, opus_path)
        os.remove(wav_path)
