import json
import re
from sqlalchemy.orm import Session
from src.llm.client import LLMClient
from src.models import Character, Novel


class CharacterAnalyzer:
    def __init__(self, llm: LLMClient, db: Session):
        self.llm = llm
        self.db = db

    async def analyze(self, novel_id: int, full_text: str) -> list[dict]:
        chunk_size = 8000
        all_chars = {}

        for start in range(0, min(len(full_text), 32000), chunk_size):
            chunk = full_text[start:start + chunk_size]
            chars = await self._analyze_chunk(chunk)
            for name, data in chars.items():
                if name in all_chars:
                    all_chars[name]["aliases"] = list(set(all_chars[name]["aliases"] + data["aliases"]))
                else:
                    all_chars[name] = data

        characters = list(all_chars.values())

        for char in characters:
            profile = await self._get_evolution(char, full_text[:12000])
            char["evolution"] = profile.get("evolution", [])
            char["base_profile"] = profile.get("base_profile", {})
            self._save_character(novel_id, char)

        novel = self.db.get(Novel, novel_id)
        if novel:
            novel.status = "characters_analyzed"
            self.db.commit()

        return characters

    async def _analyze_chunk(self, text: str) -> dict[str, dict]:
        """Extract character names and aliases from text chunk."""
        prompt = f"""从以下小说片段中找出所有角色（人物）。对每个角色列出其所有不同称呼（姓名、昵称、称号等）。

要求：只输出角色名和别名，每行一个角色，格式为：
角色名 | 别名1, 别名2, ...

小说片段：
{text}"""

        result = await self.llm.chat("", prompt)
        chars = {}
        for line in result.strip().split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 1)
            name = parts[0].strip().strip("**").strip()
            if not name:
                continue
            aliases = []
            if len(parts) > 1:
                aliases = [a.strip() for a in parts[1].split(",") if a.strip()]
            chars[name] = {"name": name, "aliases": aliases}
        return chars

    async def _get_evolution(self, char: dict, full_text: str) -> dict:
        """Get character profile and evolution phases."""
        prompt = f"""角色名：{char['name']}
别名：{', '.join(char.get('aliases', []))}

根据以下小说内容，输出该角色的：
1. 基础设定（性别、年龄范围、背景身份）
2. 性格演变阶段（按章节范围划分）

格式要求：
基础设定：性别=男, 年龄范围=20-30, 背景=江湖散人
演变阶段1：章节范围=1-15, 性格=开朗豪爽, 说话风格=语气直率
演变阶段2：章节范围=16-30, 性格=沉默寡言, 说话风格=语气低沉

小说内容：
{full_text[:8000]}"""

        result = await self.llm.chat("", prompt)
        return self._parse_evolution(result, char["name"])

    def _parse_evolution(self, text: str, name: str) -> dict:
        base_profile = {"gender": "未知", "age_range": "未知", "background": ""}
        evolution = []

        for line in text.split("\n"):
            line = line.strip()
            if "基础设定" in line:
                for part in line.split("基础设定")[-1].split(","):
                    part = part.strip()
                    if "性别" in part:
                        base_profile["gender"] = part.split("=")[-1].strip()
                    elif "年龄" in part:
                        base_profile["age_range"] = part.split("=")[-1].strip()
                    elif "背景" in part:
                        base_profile["background"] = part.split("=")[-1].strip()
                    elif "身份" in part:
                        if not base_profile["background"]:
                            base_profile["background"] = part.split("=")[-1].strip()

            phase_match = re.match(r"演变阶段(\d+)[：:]", line)
            if phase_match:
                phase = {"phase": int(phase_match.group(1)), "chapter_range": [0, 999]}
                rest = line.split("：")[-1] if "：" in line else line.split(":")[-1]
                for part in rest.split(","):
                    part = part.strip()
                    if "章节范围" in part:
                        range_str = part.split("=")[-1].strip()
                        if "-" in range_str:
                            nums = range_str.split("-")
                            phase["chapter_range"] = [int(n) for n in nums if n.strip().isdigit()]
                    elif "性格" in part:
                        phase["personality"] = part.split("=")[-1].strip() if "=" in part else part
                    elif "说话风格" in part or "语气" in part:
                        phase["speaking_style"] = part.split("=")[-1].strip() if "=" in part else part
                evolution.append(phase)

        return {"base_profile": base_profile, "evolution": evolution}

    def _save_character(self, novel_id: int, char_data: dict):
        existing = self.db.query(Character).filter_by(novel_id=novel_id, name=char_data["name"]).first()
        if existing:
            existing.aliases = char_data.get("aliases", [])
            existing.base_profile = char_data.get("base_profile", {})
            existing.evolution = char_data.get("evolution", [])
        else:
            c = Character(
                novel_id=novel_id,
                name=char_data["name"],
                aliases=char_data.get("aliases", []),
                base_profile=char_data.get("base_profile", {}),
                evolution=char_data.get("evolution", []),
            )
            self.db.add(c)
        self.db.flush()
