import os
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Novel, Chapter, Character, Sentence
from src.pipeline.orchestrator import PipelineOrchestrator
from src.config import AUDIO_OUTPUT_DIR

router = APIRouter()
orchestrator = PipelineOrchestrator()


@router.get("/novels")
def list_novels(db: Session = Depends(get_db)):
    novels = db.query(Novel).order_by(Novel.created_at.desc()).all()
    return [{"id": n.id, "title": n.title, "author": n.author,
             "file_type": n.file_type, "status": n.status,
             "created_at": str(n.created_at)} for n in novels]


@router.post("/novels")
async def create_novel(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(""),
    db: Session = Depends(get_db),
):
    file_type = file.filename.rsplit(".", 1)[-1].lower()
    if file_type not in ("txt", "epub", "mobi"):
        raise HTTPException(400, "Unsupported file type. Use txt, epub, or mobi.")

    novel = Novel(title=title, author=author, file_type=file_type, status="imported")
    db.add(novel)
    db.commit()
    db.refresh(novel)

    upload_dir = f"data/uploads/{novel.id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    novel.file_path = file_path
    db.commit()

    asyncio.create_task(orchestrator.run(novel.id))
    return {"id": novel.id, "status": "imported"}


@router.get("/novels/{novel_id}")
def get_novel(novel_id: int, db: Session = Depends(get_db)):
    novel = db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(404, "Novel not found")

    chapters = db.query(Chapter).filter_by(novel_id=novel_id).order_by(Chapter.chapter_index).all()
    return {
        "id": novel.id,
        "title": novel.title,
        "author": novel.author,
        "status": novel.status,
        "chapters": [{"id": ch.id, "index": ch.chapter_index,
                       "title": ch.title, "status": ch.status,
                       "sentence_count": ch.sentence_count} for ch in chapters],
    }


@router.delete("/novels/{novel_id}")
def delete_novel(novel_id: int, db: Session = Depends(get_db)):
    novel = db.get(Novel, novel_id)
    if not novel:
        raise HTTPException(404, "Novel not found")

    db.query(Character).filter_by(novel_id=novel_id).delete()
    chapters = db.query(Chapter).filter_by(novel_id=novel_id).all()
    for ch in chapters:
        db.query(Sentence).filter_by(chapter_id=ch.id).delete()
    db.query(Chapter).filter_by(novel_id=novel_id).delete()
    db.delete(novel)
    db.commit()

    audio_dir = os.path.join(AUDIO_OUTPUT_DIR, str(novel_id))
    if os.path.exists(audio_dir):
        import shutil
        shutil.rmtree(audio_dir)

    return {"status": "deleted"}


@router.get("/novels/{novel_id}/characters")
def get_characters(novel_id: int, db: Session = Depends(get_db)):
    chars = db.query(Character).filter_by(novel_id=novel_id).all()
    return [{"id": c.id, "name": c.name, "aliases": c.aliases,
             "base_profile": c.base_profile, "evolution": c.evolution,
             "voice_ref_id": c.voice_ref_id} for c in chars]
