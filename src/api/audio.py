import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from src.config import AUDIO_OUTPUT_DIR

router = APIRouter()


@router.get("/audio/{novel_id}/{chapter_id}/{sentence_seq}")
def get_audio(novel_id: int, chapter_id: int, sentence_seq: str):
    opus_path = os.path.join(AUDIO_OUTPUT_DIR, str(novel_id), str(chapter_id), f"sentence_{sentence_seq}.opus")
    wav_path = opus_path.replace(".opus", ".wav")

    if os.path.exists(opus_path):
        return FileResponse(opus_path, media_type="audio/ogg")
    elif os.path.exists(wav_path):
        return FileResponse(wav_path, media_type="audio/wav")
    raise HTTPException(404, "Audio not found")
