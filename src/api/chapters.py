from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Novel, Chapter, Sentence

router = APIRouter()


@router.get("/novels/{novel_id}/chapters/{chapter_id}/sentences")
def get_sentences(novel_id: int, chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter_by(id=chapter_id, novel_id=novel_id).first()
    if not chapter:
        raise HTTPException(404, "Chapter not found")

    sentences = db.query(Sentence).filter_by(chapter_id=chapter_id).order_by(Sentence.sentence_index).all()
    return [{
        "index": s.sentence_index,
        "text": s.text,
        "speaker": s.speaker,
        "emotion": s.emotion,
        "audio_url": f"/api/audio/{novel_id}/{chapter_id}/{s.sentence_index:05d}" if s.audio_path else None,
        "duration": s.audio_duration,
    } for s in sentences]
