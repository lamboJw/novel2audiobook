from sqlalchemy.orm import Session
from src.llm.client import LLMClient
from src.models import Character, VoiceLibrary


class VoiceMatcher:
    def __init__(self, llm: LLMClient, db: Session):
        self.llm = llm
        self.db = db

    async def match(self, character: Character) -> int:
        candidates = self.db.query(VoiceLibrary).all()
        if not candidates:
            raise ValueError("Voice library is empty")

        candidate_lines = "\n".join(
            f"ID {c.id}: {c.name} ({c.gender}, {c.age_group}) - {c.description}"
            for c in candidates
        )

        prompt = (
            f"为角色「{character.name}」选择最合适的音色 ID。\n"
            f"基础设定：{character.base_profile}\n"
            f"可选音色：\n{candidate_lines}\n"
            f"只返回一个数字 ID。"
        )

        result = await self.llm.chat("", prompt)
        for word in result.strip().split():
            if word.isdigit():
                return int(word)
        return candidates[0].id

    async def match_all(self, novel_id: int):
        chars = self.db.query(Character).filter_by(novel_id=novel_id).all()
        for char in chars:
            if char.voice_ref_id is not None:
                continue
            char.voice_ref_id = await self.match(char)
        self.db.commit()
