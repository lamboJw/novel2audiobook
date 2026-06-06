import json
import re
from sqlalchemy.orm import Session
from src.llm.client import LLMClient
from src.models import Sentence, Chapter

EMOTION_MAP = {
    "高兴": [0.8, 0, 0, 0, 0, 0, 0, 0.2],
    "愤怒": [0, 0.8, 0, 0, 0, 0, 0, 0.2],
    "悲伤": [0, 0, 0.8, 0, 0, 0, 0, 0.2],
    "害怕": [0, 0, 0, 0.8, 0, 0, 0.2, 0],
    "厌恶": [0, 0, 0, 0, 0.8, 0, 0.2, 0],
    "忧郁": [0, 0, 0, 0, 0.8, 0, 0.2, 0],
    "惊讶": [0.2, 0, 0, 0, 0, 0, 0.8, 0],
    "平静": [0, 0, 0, 0, 0, 0, 0, 1.0],
}

SENTENCE_RE = re.compile(r"([^。！？\n]+[。！？]|[^。！？\n]+)")


class SentenceAnalyzer:
    def __init__(self, llm: LLMClient, db: Session):
        self.llm = llm
        self.db = db

    async def analyze_chapter(self, novel_id: int, chapter_id: int,
                                chapter_text: str, characters: list) -> list[dict]:
        result = []

        sentences = self._split_sentences(chapter_text)
        batch_size = 5

        for i in range(0, len(sentences), batch_size):
            batch = sentences[i:i + batch_size]
            batch_result = await self._analyze_batch(batch, i, characters)
            result.extend(batch_result)
            self._save_sentences(chapter_id, batch_result)
            self.db.flush()

        ch = self.db.get(Chapter, chapter_id)
        if ch:
            ch.sentence_count = len(result)
            ch.status = "analyzing"
            self.db.commit()

        return result

    def _split_sentences(self, text: str) -> list[str]:
        return [s.strip() for s in SENTENCE_RE.findall(text) if s.strip()]

    async def _analyze_batch(self, sentences: list[str], start_idx: int, characters: list) -> list[dict]:
        char_names = [c.name for c in characters] if characters else []
        char_context = f"已知角色：{', '.join(char_names)}" if char_names else ""

        numbered = "\n".join(f"{i + start_idx}. {s}" for i, s in enumerate(sentences))

        prompt = (f"分析以下每句话的说话人和情感。\n"
                  f"说话人：角色名或'旁白'\n"
                  f"情感：高兴/愤怒/悲伤/害怕/厌恶/忧郁/惊讶/平静\n"
                  f"{char_context}\n\n"
                  f"格式要求：每行输出 序号|说话人|情感\n\n"
                  f"{numbered}")

        result = await self.llm.chat("", prompt)
        return self._parse_result(result, sentences, start_idx)

    def _parse_result(self, text: str, sentences: list[str], start_idx: int) -> list[dict]:
        result = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|")
            try:
                idx = int(parts[0].strip()) - start_idx
                if idx < 0 or idx >= len(sentences):
                    continue
                speaker = parts[1].strip() if len(parts) > 1 else "旁白"
                emotion = parts[2].strip() if len(parts) > 2 else "平静"
                emotion = emotion if emotion in EMOTION_MAP else "平静"
                result.append({
                    "sentence_index": idx + start_idx,
                    "text": sentences[idx],
                    "speaker": speaker,
                    "emotion": emotion,
                    "emotion_vector": json.dumps(EMOTION_MAP[emotion]),
                })
            except (ValueError, IndexError):
                continue
        return result

    def _save_sentences(self, chapter_id: int, data: list[dict]):
        for item in data:
            existing = self.db.query(Sentence).filter_by(
                chapter_id=chapter_id, sentence_index=item["sentence_index"]
            ).first()
            if existing:
                existing.speaker = item["speaker"]
                existing.emotion = item["emotion"]
                existing.emotion_vector = item["emotion_vector"]
                existing.text = item["text"]
            else:
                self.db.add(Sentence(
                    chapter_id=chapter_id,
                    sentence_index=item["sentence_index"],
                    text=item["text"],
                    speaker=item["speaker"],
                    emotion=item["emotion"],
                    emotion_vector=item["emotion_vector"],
                ))
