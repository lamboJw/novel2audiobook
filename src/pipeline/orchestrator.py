import os
import json
import asyncio
import logging
from sqlalchemy.orm import Session
from src.config import AUDIO_OUTPUT_DIR
from src.database import SessionLocal
from src.models import Novel, Chapter, Sentence, Character, VoiceLibrary
from src.parser.txt_parser import TxtParser
from src.parser.epub_parser import EpubParser
from src.parser.mobi_parser import MobiParser
from src.llm.client import LLMClient
from src.llm.character_analyzer import CharacterAnalyzer
from src.llm.sentence_analyzer import SentenceAnalyzer
from src.voice.matcher import VoiceMatcher
from src.tts.engine import TTSEngine
from src.audio.compressor import AudioCompressor

logger = logging.getLogger(__name__)

PARSERS = {
    "txt": TxtParser(),
    "epub": EpubParser(),
    "mobi": MobiParser(),
}


class PipelineOrchestrator:
    def __init__(self):
        self.llm = LLMClient()
        self.tts = TTSEngine()
        self.compressor = AudioCompressor()

    async def run(self, novel_id: int):
        db = SessionLocal()
        try:
            novel = db.get(Novel, novel_id)
            if not novel:
                logger.error(f"Novel {novel_id} not found")
                return

            novel.status = "processing"
            db.commit()

            parser = PARSERS.get(novel.file_type)
            if not parser:
                raise ValueError(f"Unsupported file type: {novel.file_type}")

            chapters = parser.parse(novel.file_path)
            for ch in chapters:
                existing = db.query(Chapter).filter_by(
                    novel_id=novel_id, chapter_index=ch.index
                ).first()
                if not existing:
                    db.add(Chapter(
                        novel_id=novel_id,
                        chapter_index=ch.index,
                        title=ch.title,
                        full_text=ch.full_text,
                        status="pending",
                        sentence_count=len(ch.sentences),
                    ))
            db.commit()

            full_text = "\n\n".join(ch.full_text for ch in chapters)
            char_analyzer = CharacterAnalyzer(self.llm, db)
            await char_analyzer.analyze(novel_id, full_text)

            matcher = VoiceMatcher(self.llm, db)
            await matcher.match_all(novel_id)

            sent_analyzer = SentenceAnalyzer(self.llm, db)
            chars = db.query(Character).filter_by(novel_id=novel_id).all()

            db_chapters = db.query(Chapter).filter_by(novel_id=novel_id).order_by(Chapter.chapter_index).all()
            for db_ch in db_chapters:
                if db_ch.status in ("done",):
                    continue
                db_ch.status = "generating"
                db.commit()

                ch_data = next(c for c in chapters if c.index == db_ch.chapter_index)
                await sent_analyzer.analyze_chapter(
                    novel_id, db_ch.id, ch_data.full_text, chars
                )

                sentences = db.query(Sentence).filter_by(chapter_id=db_ch.id).order_by(Sentence.sentence_index).all()
                for sent in sentences:
                    if sent.audio_path and os.path.exists(sent.audio_path):
                        continue
                    char = db.query(Character).filter_by(
                        novel_id=novel_id, name=sent.speaker
                    ).first()
                    if not char or not char.voice_ref_id:
                        logger.warning(f"No voice for speaker {sent.speaker}, skipping")
                        continue

                    voice = db.get(VoiceLibrary, char.voice_ref_id)
                    if not voice or not os.path.exists(voice.audio_path):
                        logger.warning(f"Voice ref {char.voice_ref_id} audio not found for {sent.speaker}")
                        continue

                    audio_dir = os.path.join(AUDIO_OUTPUT_DIR, str(novel_id), str(db_ch.chapter_index))
                    wav_path = os.path.join(audio_dir, f"sentence_{sent.sentence_index:05d}.wav")
                    opus_path = wav_path.replace(".wav", ".opus")

                    try:
                        ev = json.loads(sent.emotion_vector) if sent.emotion_vector else [0, 0, 0, 0, 0, 0, 0, 1.0]
                        await self.tts.generate(sent.text, voice.audio_path, ev, wav_path)
                        self.compressor.compress_and_cleanup(wav_path, opus_path)
                        sent.audio_path = opus_path
                        db.commit()
                    except Exception as e:
                        logger.error(f"TTS failed sent {sent.sentence_index}: {e}")
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                        continue

                db_ch.status = "done"
                db.commit()

            novel.status = "done"
            db.commit()
        except Exception as e:
            logger.error(f"Pipeline failed for novel {novel_id}: {e}")
            try:
                novel = db.get(Novel, novel_id)
                if novel:
                    novel.status = "error"
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
