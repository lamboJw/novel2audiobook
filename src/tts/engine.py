import os
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from src.config import INDEXTTS_PATH


class TTSEngine:
    def __init__(self, use_fp16: bool = True):
        self.index_path = INDEXTTS_PATH
        self.use_fp16 = use_fp16
        self._tts = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _lazy_init(self):
        if self._tts is not None:
            return
        sys.path.insert(0, self.index_path)
        from indextts.infer_v2 import IndexTTS2
        cfg = os.path.join(self.index_path, "checkpoints", "config.yaml")
        model_dir = os.path.join(self.index_path, "checkpoints")
        self._tts = IndexTTS2(
            cfg_path=cfg,
            model_dir=model_dir,
            use_fp16=self.use_fp16,
            use_cuda_kernel=False,
            use_deepspeed=False,
        )

    def generate_sync(self, text: str, voice_ref_path: str,
                      emotion_vector: list[float], output_path: str):
        self._lazy_init()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self._tts.infer(
            spk_audio_prompt=voice_ref_path,
            text=text,
            output_path=output_path,
            emo_vector=emotion_vector,
            use_emo_text=True,
            emo_text=text,
            use_random=False,
            verbose=False,
        )

    async def generate(self, text: str, voice_ref_path: str,
                       emotion_vector: list[float], output_path: str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor,
            self.generate_sync,
            text, voice_ref_path, emotion_vector, output_path,
        )
