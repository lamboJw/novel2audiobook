# 小说转有声书系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建完整的小说转有声书系统，支持 TXT/EPUB/MOBI 导入、LLM 角色和情感分析、IndexTTS2 语音生成、Web 播放器和 Android 客户端。

**Architecture:** 后端 FastAPI + MySQL 存储元数据，LLM 分析管线与 TTS 管线顺序执行，生成 Opus 音频文件通过 REST API 提供给 Web/Android 播放器。

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, PyMySQL, IndexTTS2, OpenAI SDK, ffmpeg, Kotlin/Jetpack Compose, ExoPlayer

---

### Task 1: 项目脚手架与数据库

**Files:**
- Create: `pyproject.toml`
- Create: `.env`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `src/database.py`
- Create: `src/models.py`
- Create: `src/main.py`
- Create: `tests/__init__.py`

**Notes:** IndexTTS2 安装在 `/Users/lambojw/work/index-tts`，使用 `uv run` 执行。本项目（`/Users/lambojw/work/audiobook`）作为独立项目，通过 `PYTHONPATH` 导入 IndexTTS2 模块。

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "novel2audiobook"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.0",
    "pymysql>=1.1.0",
    "python-dotenv>=1.0.0",
    "openai>=1.55.0",
    "pydantic>=2.0.0",
    "ebooklib>=0.18",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "pydub>=0.25",
    "python-multipart>=0.0.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
]
```

- [ ] **Step 2: Create .env**

```
DATABASE_URL=mysql+pymysql://root:jiawei1994@192.168.31.59:3306/novel2audiobook?charset=utf8mb4
LLM_BASE_URL=http://127.0.0.1:12434/v1
LLM_MODEL=Qwopus3.5-4B-v3-4bit
LLM_TIMEOUT=1800
LLM_MAX_CONCURRENCY=4
AUDIO_OUTPUT_DIR=data/audio
INDEXTTS_PATH=/Users/lambojw/work/index-tts
```

- [ ] **Step 3: Create src/config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:12434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwopus3.5-4B-v3-4bit")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "1800"))
LLM_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "4"))
AUDIO_OUTPUT_DIR = os.getenv("AUDIO_OUTPUT_DIR", "data/audio")
INDEXTTS_PATH = os.getenv("INDEXTTS_PATH", "/Users/lambojw/work/index-tts")
```

- [ ] **Step 4: Create src/database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 5: Create src/models.py**

```python
from sqlalchemy import Column, Integer, BigInteger, String, Text, Float, Enum, DateTime, JSON, ForeignKey, LONGTEXT
from sqlalchemy.sql import func
from src.database import Base


class Novel(Base):
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    author = Column(String(128), default="")
    language = Column(String(10), default="zh")
    file_type = Column(String(10), nullable=False)
    file_path = Column(String(512))
    status = Column(Enum("imported", "characters_analyzed", "processing", "done", "error"), default="imported")
    created_at = Column(DateTime, server_default=func.now())


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    chapter_index = Column(Integer, nullable=False)
    title = Column(String(255), default="")
    full_text = Column(LONGTEXT)
    status = Column(Enum("pending", "analyzing", "generating", "done", "error"), default="pending")
    sentence_count = Column(Integer, default=0)


class Sentence(Base):
    __tablename__ = "sentences"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    sentence_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    speaker = Column(String(128))
    emotion = Column(String(32))
    emotion_vector = Column(String(64))
    audio_duration = Column(Float)
    audio_path = Column(String(512))


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(Integer, ForeignKey("novels.id"), nullable=False)
    name = Column(String(64), nullable=False)
    aliases = Column(JSON)
    base_profile = Column(JSON)
    evolution = Column(JSON)
    voice_ref_id = Column(Integer, ForeignKey("voice_library.id"))


class VoiceLibrary(Base):
    __tablename__ = "voice_library"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    gender = Column(String(8))
    age_group = Column(String(32))
    description = Column(Text)
    audio_path = Column(String(512))
    source = Column(String(64))
```

- [ ] **Step 6: Create src/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.database import init_db
from src.api.novels import router as novels_router
from src.api.chapters import router as chapters_router
from src.api.audio import router as audio_router

app = FastAPI(title="Novel2Audiobook")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="src/static"), name="static")
app.include_router(novels_router, prefix="/api")
app.include_router(chapters_router, prefix="/api")
app.include_router(audio_router, prefix="/api")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Novel2Audiobook API running"}
```

- [ ] **Step 7: Create tests/__init__.py** (empty)

- [ ] **Step 8: Run test to verify project loads**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv sync
uv run python -c "from src.main import app; print('OK')"
```
Expected: Prints "OK"

- [ ] **Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: project scaffold with database models and FastAPI app"
```

---

### Task 2: 小说文件解析器

**Files:**
- Create: `src/parser/__init__.py`
- Create: `src/parser/base.py`
- Create: `src/parser/txt_parser.py`
- Create: `src/parser/epub_parser.py`
- Create: `src/parser/mobi_parser.py`
- Create: `tests/test_parser.py`

**Note:** 需要 `ebooklib`、`beautifulsoup4`、`lxml` 依赖。

- [ ] **Step 1: Create src/parser/__init__.py** (empty)

- [ ] **Step 2: Create src/parser/base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Chapter:
    index: int
    title: str
    sentences: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "".join(self.sentences)


class NovelParser(ABC):
    @abstractmethod
    def parse(self, path: str) -> list[Chapter]:
        pass
```

- [ ] **Step 3: Create src/parser/txt_parser.py**

```python
import re
from src.parser.base import NovelParser, Chapter

CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千零0-9]+章.*$", re.MULTILINE)
SENTENCE_RE = re.compile(r"[^。！？\n]+[。！？]|[^。！？\n]+$")


class TxtParser(NovelParser):
    def parse(self, path: str) -> list[Chapter]:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        text = text.strip()
        parts = CHAPTER_RE.split(text)
        titles = CHAPTER_RE.findall(text)

        chapters = []
        if len(parts) <= 1:
            chapters.append(Chapter(index=0, title="全文", sentences=self._split_sentences(text)))
        else:
            for i, content in enumerate(parts):
                if not content.strip():
                    continue
                title = titles[i - 1] if i > 0 else "前言"
                chapters.append(Chapter(index=i, title=title.strip(), sentences=self._split_sentences(content.strip())))

        return chapters

    def _split_sentences(self, text: str) -> list[str]:
        sentences = SENTENCE_RE.findall(text)
        return [s.strip() for s in sentences if s.strip()]
```

- [ ] **Step 4: Create src/parser/epub_parser.py**

```python
from ebooklib import epub
from bs4 import BeautifulSoup
from src.parser.base import NovelParser, Chapter
import re

SENTENCE_RE = re.compile(r"[^。！？\n]+[。！？]|[^。！？\n]+$")


class EpubParser(NovelParser):
    def parse(self, path: str) -> list[Chapter]:
        book = epub.read_epub(path)
        chapters = []
        index = 0
        for item in book.get_items():
            if item.get_type() == 9:  # ITEM_DOCUMENT
                soup = BeautifulSoup(item.get_content(), "html.parser")
                text = soup.get_text().strip()
                if not text:
                    continue
                title_tag = soup.find(["h1", "h2", "h3"])
                title = title_tag.get_text().strip() if title_tag else f"第{index+1}章"
                sentences = SENTENCE_RE.findall(text)
                sentences = [s.strip() for s in sentences if s.strip()]
                if sentences:
                    chapters.append(Chapter(index=index, title=title, sentences=sentences))
                    index += 1
        return chapters
```

- [ ] **Step 5: Create src/parser/mobi_parser.py**

```python
import subprocess
import tempfile
import os
from src.parser.base import NovelParser, Chapter
from src.parser.epub_parser import EpubParser


class MobiParser(NovelParser):
    def parse(self, path: str) -> list[Chapter]:
        try:
            import mobi
            temp_dir = tempfile.mkdtemp()
            _, filepath = mobi.extract(path, temp_dir)
            epub_path = None
            for f in os.listdir(filepath):
                if f.endswith(".epub") or f.endswith(".html"):
                    epub_path = os.path.join(filepath, f)
                    break
            if epub_path and epub_path.endswith(".epub"):
                parser = EpubParser()
                return parser.parse(epub_path)
            elif epub_path:
                parser = TxtParser()
                return parser.parse(epub_path)
            else:
                raise ValueError("Could not extract content from MOBI")
        except ImportError:
            raise ImportError("mobi package not available. Install with: uv pip install mobi")
```

- [ ] **Step 6: Create tests/test_parser.py**

```python
import pytest
import tempfile
import os
from src.parser.txt_parser import TxtParser


SAMPLE_TXT = """第一章 初遇
    
张三走在街上。天色已晚。

第二章 重逢
    
两人在茶馆相遇。三哥笑了笑。
"""


def test_txt_parser_splits_chapters():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE_TXT)
        path = f.name

    try:
        parser = TxtParser()
        chapters = parser.parse(path)
        assert len(chapters) == 2
        assert chapters[0].title == "第一章 初遇"
        assert chapters[0].sentences[0] == "张三走在街上。"
        assert chapters[1].title == "第二章 重逢"
        assert chapters[1].sentences[1] == "三哥笑了笑。"
    finally:
        os.unlink(path)


def test_txt_parser_single_chapter():
    text = "这是一段话。这是另一句。"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        parser = TxtParser()
        chapters = parser.parse(path)
        assert len(chapters) == 1
        assert chapters[0].title == "全文"
        assert len(chapters[0].sentences) == 2
    finally:
        os.unlink(path)
```

- [ ] **Step 7: Run tests**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run pytest tests/test_parser.py -v
```
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add src/parser/ tests/test_parser.py
git commit -m "feat: add novel file parsers (txt/epub/mobi)"
```

---

### Task 3: LLM 客户端

**Files:**
- Create: `src/llm/__init__.py`
- Create: `src/llm/client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Create src/llm/__init__.py** (empty)

- [ ] **Step 2: Create src/llm/client.py**

```python
import json
import asyncio
from openai import AsyncOpenAI
from src.config import LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_CONCURRENCY


class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=LLM_BASE_URL,
            api_key="not-needed",
            timeout=LLM_TIMEOUT
        )
        self.model = LLM_MODEL
        self.semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENCY)

    async def chat(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                async with self.semaphore:
                    resp = await self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=4096,
                    )
                    return resp.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        text = await self.chat(system_prompt, user_prompt)
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        return json.loads(text)
```

- [ ] **Step 3: Create tests/test_llm_client.py**

```python
import pytest
from src.llm.client import LLMClient


@pytest.mark.asyncio
async def test_llm_client_returns_string():
    client = LLMClient()
    result = await client.chat("Say hello", "Say hello in Chinese")
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 4: Run test**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run pytest tests/test_llm_client.py -v --timeout=600
```
Expected: PASS (requires LLM server running)

- [ ] **Step 5: Commit**

```bash
git add src/llm/ tests/test_llm_client.py
git commit -m "feat: add LLM client with retry and concurrency control"
```

---

### Task 4: LLM 角色分析器

**Files:**
- Create: `src/llm/character_analyzer.py`
- Create: `tests/test_character_analyzer.py`

- [ ] **Step 1: Create src/llm/character_analyzer.py**

```python
import json
from sqlalchemy.orm import Session
from src.llm.client import LLMClient
from src.models import Character, Novel

CHARACTER_SYSTEM_PROMPT = """你是小说角色分析专家。分析文本中所有角色，注意：
1. 不同称呼可能指向同一人（如张三/三哥/张兄）
2. 角色性格可能随剧情演变"""


class CharacterAnalyzer:
    def __init__(self, llm: LLMClient, db: Session):
        self.llm = llm
        self.db = db

    async def analyze(self, novel_id: int, full_text: str) -> list[dict]:
        chunk_size = 8000
        characters_map = {}

        for start in range(0, len(full_text), chunk_size):
            chunk = full_text[start:start + chunk_size]
            user_prompt = f"分析以下小说片段中的角色：\n\n{chunk}"
            result = await self.llm.chat_json(CHARACTER_SYSTEM_PROMPT, user_prompt)
            for char in result:
                name = char["name"]
                if name in characters_map:
                    existing = characters_map[name]
                    existing["aliases"] = list(set(existing["aliases"] + char.get("aliases", [])))
                else:
                    characters_map[name] = char

        characters = list(characters_map.values())

        for char in characters:
            evolution_prompt = (
                f"角色「{char['name']}」的别名有：{char.get('aliases', [])}。"
                f"基础设定：{json.dumps(char.get('base_profile', {}), ensure_ascii=False)}。"
                f"分析该角色在整个故事中的性格演变阶段，按章节范围划分。"
                f"全文：\n{full_text[:12000]}"
            )
            phases = await self.llm.chat_json(
                "识别角色性格演变阶段，输出 JSON 数组。",
                evolution_prompt
            )
            char["evolution"] = phases if isinstance(phases, list) else []
            self._save_character(novel_id, char)

        return characters

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
```

- [ ] **Step 2: Create tests/test_character_analyzer.py**

```python
import pytest
from src.llm.client import LLMClient
from src.llm.character_analyzer import CharacterAnalyzer
from src.database import SessionLocal, init_db
from src.models import Novel


@pytest.mark.asyncio
async def test_character_analyzer_extracts_names():
    init_db()
    text = "张三走进茶馆。王五站起来说：'三哥，好久不见！'"
    session = SessionLocal()
    novel = Novel(title="测试", author="测试", file_type="txt")
    session.add(novel)
    session.commit()

    try:
        llm = LLMClient()
        analyzer = CharacterAnalyzer(llm, session)
        chars = await analyzer.analyze(novel.id, text)
        assert len(chars) >= 1
        names = [c["name"] for c in chars]
        assert "张三" in names or "王五" in names
        if "张三" in names:
            zhangsan = next(c for c in chars if c["name"] == "张三")
            assert "三哥" in zhangsan.get("aliases", [])
    finally:
        session.close()
```

- [ ] **Step 3: Run test**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run pytest tests/test_character_analyzer.py -v --timeout=600
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/llm/character_analyzer.py tests/test_character_analyzer.py
git commit -m "feat: add LLM character analyzer with alias resolution and evolution detection"
```

---

### Task 5: LLM 逐句分析器

**Files:**
- Create: `src/llm/sentence_analyzer.py`
- Create: `tests/test_sentence_analyzer.py`

- [ ] **Step 1: Create src/llm/sentence_analyzer.py**

```python
import json
from sqlalchemy.orm import Session
from src.llm.client import LLMClient
from src.models import Sentence, Chapter, Character

EMOTION_MAP = {
    "高兴": [0.8, 0, 0, 0, 0, 0, 0, 0.2],
    "愤怒": [0, 0.8, 0, 0, 0, 0, 0, 0.2],
    "悲伤": [0, 0, 0.8, 0, 0, 0, 0, 0.2],
    "害怕": [0, 0, 0, 0.8, 0, 0, 0.2, 0],
    "厌恶": [0, 0, 0, 0, 0.8, 0, 0.2, 0],
    "忧郁": [0, 0, 0, 0, 0, 0.8, 0, 0.2],
    "惊讶": [0.2, 0, 0, 0, 0, 0, 0.8, 0],
    "平静": [0, 0, 0, 0, 0, 0, 0, 1.0],
}

SYSTEM_PROMPT = """分析以下章节每句话的说话人和情感。
- 说话人：角色名（规范名）或"旁白"
- 情感：从 [高兴, 愤怒, 悲伤, 害怕, 厌恶, 忧郁, 惊讶, 平静] 选一个
输出 JSON 数组：[{"sentence_index":N,"text":"...","speaker":"...","emotion":"..."}]"""


class SentenceAnalyzer:
    def __init__(self, llm: LLMClient, db: Session):
        self.llm = llm
        self.db = db

    async def analyze_chapter(self, novel_id: int, chapter_id: int,
                                chapter_text: str, characters: list[Character]) -> list[dict]:
        char_context = self._build_context(characters, chapter_id)
        user_prompt = (
            f"角色性格阶段参考：\n{char_context}\n\n"
            f"章节内容：\n{chapter_text}"
        )
        result = await self.llm.chat_json(SYSTEM_PROMPT, user_prompt)

        for item in result:
            emotion_cn = item["emotion"]
            item["emotion"] = emotion_cn
            item["emotion_vector"] = json.dumps(EMOTION_MAP.get(emotion_cn, EMOTION_MAP["平静"]))
            self._save_sentence(chapter_id, item)

        return result

    def _build_context(self, characters: list[Character], chapter_id: int) -> str:
        lines = []
        for c in characters:
            if not c.evolution:
                continue
            for phase in c.evolution:
                if not isinstance(phase, dict):
                    continue
                cr = phase.get("chapter_range", [0, 9999])
                ch = self.db.query(Chapter).get(chapter_id)
                if not ch:
                    continue
                if cr[0] <= ch.chapter_index <= cr[1]:
                    lines.append(f"{c.name}: {phase.get('personality', '')}")
        return "\n".join(lines) if lines else "无特殊性格阶段"

    def _save_sentence(self, chapter_id: int, data: dict):
        s = Sentence(
            chapter_id=chapter_id,
            sentence_index=data["sentence_index"],
            text=data["text"],
            speaker=data["speaker"],
            emotion=data["emotion"],
            emotion_vector=data.get("emotion_vector"),
        )
        self.db.add(s)
```

- [ ] **Step 2: Create tests/test_sentence_analyzer.py**

```python
import pytest
from src.llm.client import LLMClient
from src.llm.sentence_analyzer import SentenceAnalyzer
from src.database import SessionLocal, init_db
from src.models import Novel, Chapter


@pytest.mark.asyncio
async def test_sentence_analyzer_returns_speakers():
    init_db()
    session = SessionLocal()
    novel = Novel(title="测试", author="测试", file_type="txt")
    session.add(novel)
    session.flush()
    chapter = Chapter(novel_id=novel.id, chapter_index=1, title="测试章")
    session.add(chapter)
    session.commit()

    text = "张三说：'你好。'王五点了点头。"
    try:
        llm = LLMClient()
        analyzer = SentenceAnalyzer(llm, session)
        result = await analyzer.analyze_chapter(novel.id, chapter.id, text, [])
        assert len(result) >= 2
        speakers = {s["speaker"] for s in result}
        assert "旁白" in speakers
    finally:
        session.close()
```

- [ ] **Step 3: Run test**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run pytest tests/test_sentence_analyzer.py -v --timeout=600
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/llm/sentence_analyzer.py tests/test_sentence_analyzer.py
git commit -m "feat: add sentence analyzer for speaker and emotion per sentence"
```

---

### Task 6: 语音库

**Files:**
- Create: `src/voice/__init__.py`
- Create: `src/voice/library.py`
- Create: `src/voice/matcher.py`
- Create: `voice_library/metadata.json`

- [ ] **Step 1: Create src/voice/__init__.py** (empty)

- [ ] **Step 2: Create src/voice/library.py**

```python
import json
from sqlalchemy.orm import Session
from src.models import VoiceLibrary


class VoiceLibraryManager:
    def __init__(self, db: Session):
        self.db = db

    def load_metadata(self, metadata_path: str):
        with open(metadata_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            existing = self.db.query(VoiceLibrary).filter_by(name=entry["name"]).first()
            if existing:
                for k, v in entry.items():
                    setattr(existing, k, v)
            else:
                self.db.add(VoiceLibrary(**entry))
        self.db.commit()

    def get_entry(self, voice_ref_id: int) -> VoiceLibrary:
        return self.db.query(VoiceLibrary).get(voice_ref_id)

    def list_all(self, gender: str = None, age_group: str = None) -> list[VoiceLibrary]:
        q = self.db.query(VoiceLibrary)
        if gender:
            q = q.filter_by(gender=gender)
        if age_group:
            q = q.filter_by(age_group=age_group)
        return q.all()
```

- [ ] **Step 3: Create src/voice/matcher.py**

```python
import json
from sqlalchemy.orm import Session
from src.llm.client import LLMClient
from src.models import Character


class VoiceMatcher:
    def __init__(self, llm: LLMClient, db: Session):
        self.llm = llm
        self.db = db

    async def match(self, character: Character) -> int:
        from src.models import VoiceLibrary
        candidates = self.db.query(VoiceLibrary).all()
        if not candidates:
            raise ValueError("Voice library is empty")

        prompt = (
            f"为以下角色匹配最合适的参考音色 ID：\n"
            f"角色名：{character.name}\n"
            f"基础设定：{json.dumps(character.base_profile, ensure_ascii=False)}\n"
            f"性格阶段：{json.dumps(character.evolution, ensure_ascii=False)}\n\n"
            f"可选音色：\n"
        )
        for c in candidates:
            prompt += f"  ID {c.id}: {c.name} ({c.gender}, {c.age_group}) - {c.description}\n"
        prompt += "\n只返回音色 ID 数字。"

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
```

- [ ] **Step 4: Create voice_library/metadata.json**

```json
[
  {
    "name": "青年男声_01",
    "gender": "male",
    "age_group": "young",
    "description": "清亮爽朗的青年男声，适合20-30岁正面主角",
    "audio_path": "voice_library/samples/male_young_01.wav",
    "source": "placeholder"
  },
  {
    "name": "中年男声_01",
    "gender": "male",
    "age_group": "middle",
    "description": "沉稳厚重的中年男声，适合掌门/父亲类角色",
    "audio_path": "voice_library/samples/male_mid_01.wav",
    "source": "placeholder"
  },
  {
    "name": "老年男声_01",
    "gender": "male",
    "age_group": "elderly",
    "description": "苍老沙哑的老年男声，适合长者/隐士",
    "audio_path": "voice_library/samples/male_old_01.wav",
    "source": "placeholder"
  },
  {
    "name": "青年女声_01",
    "gender": "female",
    "age_group": "young",
    "description": "甜美清脆的青年女声，适合女主角",
    "audio_path": "voice_library/samples/female_young_01.wav",
    "source": "placeholder"
  },
  {
    "name": "中年女声_01",
    "gender": "female",
    "age_group": "middle",
    "description": "温婉柔和的中年女声，适合母亲/师娘",
    "audio_path": "voice_library/samples/female_mid_01.wav",
    "source": "placeholder"
  },
  {
    "name": "旁白_男_01",
    "gender": "male",
    "age_group": "middle",
    "description": "中性沉稳的旁白叙事音色",
    "audio_path": "voice_library/samples/narrator_male_01.wav",
    "source": "placeholder"
  }
]
```

- [ ] **Step 5: Create voice_library/samples/ directory**

Run:
```bash
mkdir -p voice_library/samples
touch voice_library/samples/.gitkeep
```

- [ ] **Step 6: Commit**

```bash
git add src/voice/ voice_library/
git commit -m "feat: add voice library manager and matcher"
```

---

### Task 7: TTS 引擎与音频压缩

**Files:**
- Create: `src/tts/__init__.py`
- Create: `src/tts/engine.py`
- Create: `src/audio/__init__.py`
- Create: `src/audio/compressor.py`
- Create: `tests/test_compressor.py`

- [ ] **Step 1: Create src/tts/__init__.py** (empty)

- [ ] **Step 2: Create src/tts/engine.py**

```python
import os
import sys
import json
import subprocess
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
```

- [ ] **Step 3: Create src/audio/__init__.py** (empty)

- [ ] **Step 4: Create src/audio/compressor.py**

```python
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
```

- [ ] **Step 5: Create tests/test_compressor.py**

```python
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
```

- [ ] **Step 6: Run compressor test**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run pytest tests/test_compressor.py -v
```
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add src/tts/ src/audio/ tests/test_compressor.py
git commit -m "feat: add TTS engine and audio compressor"
```

---

### Task 8: 管线编排器

**Files:**
- Create: `src/pipeline/__init__.py`
- Create: `src/pipeline/orchestrator.py`

- [ ] **Step 1: Create src/pipeline/__init__.py** (empty)

- [ ] **Step 2: Create src/pipeline/orchestrator.py**

```python
import os
import json
import asyncio
import logging
from sqlalchemy.orm import Session
from src.config import AUDIO_OUTPUT_DIR
from src.database import SessionLocal
from src.models import Novel, Chapter, Sentence, Character
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
            novel = db.query(Novel).get(novel_id)
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
            if novel.status == "imported":
                char_analyzer = CharacterAnalyzer(self.llm, db)
                await char_analyzer.analyze(novel_id, full_text)
                novel.status = "characters_analyzed"
                db.commit()

            matcher = VoiceMatcher(self.llm, db)
            await matcher.match_all(novel_id)

            sent_analyzer = SentenceAnalyzer(self.llm, db)
            chars = db.query(Character).filter_by(novel_id=novel_id).all()

            db_chapters = db.query(Chapter).filter_by(novel_id=novel_id).order_by(Chapter.chapter_index).all()
            for db_ch in db_chapters:
                if db_ch.status in ("done", "generating"):
                    continue
                db_ch.status = "generating"
                db.commit()

                ch_data = next(c for c in chapters if c.index == db_ch.chapter_index)
                if db_ch.status == "pending":
                    await sent_analyzer.analyze_chapter(
                        novel_id, db_ch.id, db_ch.full_text, chars
                    )

                sentences = db.query(Sentence).filter_by(chapter_id=db_ch.id).order_by(Sentence.sentence_index).all()
                for sent in sentences:
                    if sent.audio_path and os.path.exists(sent.audio_path):
                        continue
                    char = db.query(Character).filter_by(
                        novel_id=novel_id, name=sent.speaker
                    ).first()
                    if not char or not char.voice_ref_id:
                        logger.warning(f"No voice for speaker {sent.speaker}, using first available")
                        first_voice = db.query(Character).filter(
                            Character.voice_ref_id.isnot(None)
                        ).first()
                        if first_voice:
                            char = first_voice
                        else:
                            logger.error(f"Cannot generate audio for {sent.speaker}: no voice")
                            continue

                    from src.models import VoiceLibrary
                    voice = db.query(VoiceLibrary).get(char.voice_ref_id)
                    if not voice:
                        logger.warning(f"Voice ref {char.voice_ref_id} not found")
                        continue

                    audio_dir = os.path.join(AUDIO_OUTPUT_DIR, str(novel_id), str(db_ch.chapter_index))
                    wav_path = os.path.join(audio_dir, f"sentence_{sent.sentence_index:05d}.wav")
                    opus_path = wav_path.replace(".wav", ".opus")

                    try:
                        await self.tts.generate(
                            sent.text, voice.audio_path,
                            json.loads(sent.emotion_vector) if sent.emotion_vector else [0]*8,
                            wav_path,
                        )
                        self.compressor.compress_and_cleanup(wav_path, opus_path)
                        sent.audio_path = opus_path
                        db.commit()
                    except Exception as e:
                        logger.error(f"Failed to generate sentence {sent.sentence_index}: {e}")
                        if os.path.exists(wav_path):
                            os.remove(wav_path)
                        continue

                db_ch.status = "done"
                db.commit()

            novel.status = "done"
            db.commit()
        except Exception as e:
            logger.error(f"Pipeline failed for novel {novel_id}: {e}")
            novel.status = "error"
            db.commit()
        finally:
            db.close()
```

- [ ] **Step 3: Commit**

```bash
git add src/pipeline/
git commit -m "feat: add pipeline orchestrator with resume support"
```

---

### Task 9: REST API

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/novels.py`
- Create: `src/api/chapters.py`
- Create: `src/api/audio.py`
- Create: `src/api/ws.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Create src/api/__init__.py** (empty)

- [ ] **Step 2: Create src/api/novels.py**

```python
import os
import json
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.models import Novel, Chapter, Character
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
    novel = db.query(Novel).get(novel_id)
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
    novel = db.query(Novel).get(novel_id)
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
```

- [ ] **Step 3: Create src/api/chapters.py**

```python
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
```

- [ ] **Step 4: Create src/api/audio.py**

```python
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/audio/{novel_id}/{chapter_id}/{sentence_seq}")
def get_audio(novel_id: int, chapter_id: int, sentence_seq: str):
    from src.config import AUDIO_OUTPUT_DIR
    opus_path = os.path.join(AUDIO_OUTPUT_DIR, str(novel_id), str(chapter_id), f"sentence_{sentence_seq}.opus")
    wav_path = opus_path.replace(".opus", ".wav")

    if os.path.exists(opus_path):
        return FileResponse(opus_path, media_type="audio/ogg")
    elif os.path.exists(wav_path):
        return FileResponse(wav_path, media_type="audio/wav")
    raise HTTPException(404, "Audio not found")
```

- [ ] **Step 5: Create src/api/ws.py**

```python
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.database import SessionLocal
from src.models import Novel

router = APIRouter()


@router.websocket("/ws/progress/{novel_id}")
async def progress_ws(websocket: WebSocket, novel_id: int):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                novel = db.query(Novel).get(novel_id)
                if not novel:
                    await websocket.send_json({"error": "not found"})
                    break
                await websocket.send_json({
                    "novel_id": novel.id,
                    "status": novel.status,
                    "title": novel.title,
                })
                if novel.status in ("done", "error"):
                    break
            finally:
                db.close()
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
```

- [ ] **Step 6: Create tests/test_api.py**

```python
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_list_novels_empty():
    resp = client.get("/api/novels")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

- [ ] **Step 7: Run API test**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run pytest tests/test_api.py -v
```
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add src/api/ tests/test_api.py
git commit -m "feat: add REST API routes for novels, chapters, and audio"
```

---

### Task 10: Web UI

**Files:**
- Create: `src/static/index.html`
- Create: `src/static/style.css`
- Create: `src/static/app.js`

- [ ] **Step 1: Create src/static/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>有声小说播放器</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div id="app">
  <aside id="sidebar">
    <h2>书架</h2>
    <ul id="novel-list"></ul>
    <hr>
    <ul id="chapter-list"></ul>
  </aside>
  <main id="content">
    <div id="reader"></div>
  </main>
  <footer id="player-bar">
    <button id="play-btn">▶</button>
    <span id="sentence-info"></span>
  </footer>
</div>
<div id="upload-modal" class="modal">
  <div class="modal-content">
    <h3>导入小说</h3>
    <form id="upload-form">
      <input type="file" id="file-input" accept=".txt,.epub,.mobi" required>
      <input type="text" id="title-input" placeholder="书名" required>
      <input type="text" id="author-input" placeholder="作者">
      <button type="submit">导入</button>
    </form>
  </div>
</div>
<script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create src/static/style.css**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "PingFang SC", "Noto Sans SC", sans-serif; display: flex; height: 100vh; background: #f5f5f5; }

#app { display: flex; width: 100%; height: 100%; }
#sidebar { width: 280px; background: #fff; border-right: 1px solid #ddd; padding: 16px; overflow-y: auto; }
#sidebar h2 { font-size: 18px; margin-bottom: 12px; }
#novel-list li, #chapter-list li { padding: 8px 12px; cursor: pointer; border-radius: 6px; list-style: none; }
#novel-list li:hover, #chapter-list li:hover { background: #e8f0fe; }
#novel-list li.active, #chapter-list li.active { background: #d0e3fc; font-weight: bold; }

#content { flex: 1; padding: 24px 40px; overflow-y: auto; padding-bottom: 80px; }
#reader { max-width: 720px; margin: 0 auto; line-height: 2; font-size: 16px; }
.sentence { cursor: pointer; padding: 2px 1px; border-radius: 3px; transition: background 0.2s; }
.sentence:hover { background: #eef; }
.sentence.playing { background: #fff3b0; }
.sentence.speaker-label { font-weight: bold; color: #666; font-size: 13px; display: block; margin-top: 8px; }

#player-bar { position: fixed; bottom: 0; left: 0; right: 0; height: 56px; background: #fff; border-top: 1px solid #ddd; display: flex; align-items: center; padding: 0 24px; gap: 16px; z-index: 100; }
#play-btn { width: 40px; height: 40px; border-radius: 50%; border: none; background: #1a73e8; color: #fff; font-size: 18px; cursor: pointer; }
#play-btn:hover { background: #1557b0; }

.modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); z-index: 200; align-items: center; justify-content: center; }
.modal.show { display: flex; }
.modal-content { background: #fff; padding: 24px; border-radius: 12px; min-width: 360px; }
.modal-content input { display: block; width: 100%; margin: 8px 0; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; }
.modal-content button { padding: 8px 24px; background: #1a73e8; color: #fff; border: none; border-radius: 6px; cursor: pointer; }

.status-badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; background: #eee; margin-left: 8px; }
.status-badge.done { background: #c8e6c9; }
.status-badge.error { background: #ffcdd2; }
```

- [ ] **Step 3: Create src/static/app.js**

```javascript
const API = "/api";
let state = { novels: [], currentNovel: null, chapters: [], sentences: [], currentIndex: -1, audio: null, playing: false };

// ---- API calls ----
async function api(path) { const r = await fetch(API + path); return r.json(); }

// ---- Novel list ----
async function loadNovels() {
  const novels = await api("/novels");
  state.novels = novels;
  const ul = document.getElementById("novel-list");
  ul.innerHTML = novels.map(n =>
    `<li onclick="selectNovel(${n.id})" class="${state.currentNovel?.id === n.id ? 'active' : ''}">
      ${n.title} <span class="status-badge ${n.status === 'done' ? 'done' : ''}">${n.status}</span>
    </li>`
  ).join("");
}

async function selectNovel(id) {
  const data = await api(`/novels/${id}`);
  state.currentNovel = data;
  state.chapters = data.chapters || [];
  const ul = document.getElementById("chapter-list");
  ul.innerHTML = state.chapters.map(ch =>
    `<li onclick="loadChapter(${data.id}, ${ch.id})">
      第${ch.index}章 ${ch.title}
      <span class="status-badge ${ch.status === 'done' ? 'done' : ''}">${ch.status}</span>
    </li>`
  ).join("");
  loadNovels();
}

// ---- Chapter ----
async function loadChapter(novelId, chapterId) {
  const sentences = await api(`/novels/${novelId}/chapters/${chapterId}/sentences`);
  state.sentences = sentences;
  state.currentIndex = -1;
  renderSentences();
}

function renderSentences() {
  const reader = document.getElementById("reader");
  reader.innerHTML = state.sentences.map((s, i) =>
    `<span class="sentence ${i === state.currentIndex ? 'playing' : ''}"
           data-index="${i}" onclick="playSentence(${i})">${escapeHtml(s.text)}</span> `
  ).join("");
}

function escapeHtml(s) { return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

// ---- Audio playback ----
function playSentence(index) {
  const s = state.sentences[index];
  if (!s || !s.audio_url) return;
  stopPlayback();

  state.currentIndex = index;
  renderSentences();
  document.getElementById("sentence-info").textContent = `${index + 1}/${state.sentences.length}`;

  state.audio = new Audio(s.audio_url);
  state.audio.onended = () => {
    if (state.currentIndex < state.sentences.length - 1) {
      playSentence(state.currentIndex + 1);
    } else {
      state.playing = false;
      document.getElementById("play-btn").textContent = "▶";
    }
  };
  state.audio.play();
  state.playing = true;
  document.getElementById("play-btn").textContent = "⏸";
}

function stopPlayback() {
  if (state.audio) { state.audio.pause(); state.audio = null; }
  state.playing = false;
  document.getElementById("play-btn").textContent = "▶";
}

document.getElementById("play-btn").onclick = () => {
  if (!state.sentences.length) return;
  if (state.playing) { stopPlayback(); return; }
  if (state.currentIndex < 0) { playSentence(0); }
  else { playSentence(state.currentIndex); }
};

// ---- Upload ----
document.getElementById("upload-form").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData();
  fd.append("file", document.getElementById("file-input").files[0]);
  fd.append("title", document.getElementById("title-input").value);
  fd.append("author", document.getElementById("author-input").value);
  await fetch(API + "/novels", { method: "POST", body: fd });
  document.getElementById("upload-modal").classList.remove("show");
  loadNovels();
};

document.querySelector(".modal").onclick = (e) => {
  if (e.target === e.currentTarget) e.currentTarget.classList.remove("show");
};

// ---- Init ----
loadNovels();
```

- [ ] **Step 4: Test Web UI loads**

Run:
```bash
cd /Users/lambojw/work/audiobook
uv run uvicorn src.main:app --reload &
sleep 2
curl -s http://127.0.0.1:8000/static/index.html | head -5
```
Expected: HTML content returned

- [ ] **Step 5: Commit**

```bash
git add src/static/
git commit -m "feat: add Web UI with novel reader and sentence-level player"
```

---

### Task 11: 语音库构建（手动步骤说明）

> 语音库的参考音频需要从开源数据集中提取。以下是操作指引，不作为自动化测试步骤。

**Steps：**
1. 下载 AISHELL-3 数据集
2. 从每个说话人的录音中选择 3-5 秒干净的语句
3. 转换为 24000Hz 单声道 WAV
4. 放入 `voice_library/samples/` 目录
5. 更新 `voice_library/metadata.json` 中的 `audio_path` 指向实际文件
6. 运行以下命令入库：

```bash
cd /Users/lambojw/work/audiobook
uv run python -c "
from src.database import SessionLocal, init_db
from src.voice.library import VoiceLibraryManager
init_db()
db = SessionLocal()
mgr = VoiceLibraryManager(db)
mgr.load_metadata('voice_library/metadata.json')
db.close()
print('Voice library loaded')
"
```

---

### Task 12: Android 客户端

> Android 客户端依赖后端 API，可在后端开发完成后独立开发。

**Files:**
- Create: `android/build.gradle.kts`
- Create: `android/settings.gradle.kts`
- Create: `android/app/build.gradle.kts`
- Create: `android/app/src/main/AndroidManifest.xml`
- Create: `android/app/src/main/java/com/novelplayer/data/ApiModels.kt`
- Create: `android/app/src/main/java/com/novelplayer/data/ApiClient.kt`
- Create: `android/app/src/main/java/com/novelplayer/data/NovelRepository.kt`
- Create: `android/app/src/main/java/com/novelplayer/player/AudioPlayerService.kt`
- Create: `android/app/src/main/java/com/novelplayer/ui/MainActivity.kt`
- Create: `android/app/src/main/java/com/novelplayer/ui/NovelListScreen.kt`
- Create: `android/app/src/main/java/com/novelplayer/ui/PlayerScreen.kt`

- [ ] **Step 1: Create project build files**

`android/settings.gradle.kts`:
```kotlin
pluginManagement {
    repositories { google(); mavenCentral() }
}
dependencyResolution { repositories { google(); mavenCentral() } }
rootProject.name = "NovelPlayer"
include(":app")
```

`android/app/build.gradle.kts`:
```kotlin
plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.novelplayer"
    compileSdk = 34
    defaultConfig { minSdk = 26; targetSdk = 34 }
    buildFeatures { compose = true }
    composeOptions { kotlinCompilerExtensionVersion = "1.5.0" }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui"); implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.8.0")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.google.android.exoplayer:exoplayer-core:2.19.0")
    implementation("com.google.android.exoplayer:exoplayer-ogg:2.19.0")
}
```

- [ ] **Step 2: Create ApiModels.kt**

```kotlin
data class Novel(val id: Int, val title: String, val author: String, val status: String)
data class ChapterInfo(val id: Int, val index: Int, val title: String, val status: String)
data class NovelDetail(val id: Int, val title: String, val chapters: List<ChapterInfo>)
data class SentenceData(val index: Int, val text: String, val speaker: String?, val emotion: String?, val audioUrl: String?)
```

- [ ] **Step 3: Create ApiClient.kt**

```kotlin
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*

interface ApiService {
    @GET("api/novels") suspend fun listNovels(): List<Novel>
    @GET("api/novels/{id}") suspend fun getNovel(@Path("id") id: Int): NovelDetail
    @GET("api/novels/{nid}/chapters/{cid}/sentences")
    suspend fun getSentences(@Path("nid") nid: Int, @Path("cid") cid: Int): List<SentenceData>
}

object ApiClient {
    private val retrofit = Retrofit.Builder()
        .baseUrl("http://192.168.31.59:8000/")
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    val service = retrofit.create(ApiService::class.java)
}
```

- [ ] **Step 4: Create NovelRepository.kt**

```kotlin
class NovelRepository {
    private val api = ApiClient.service

    suspend fun listNovels() = api.listNovels()
    suspend fun getNovel(id: Int) = api.getNovel(id)
    suspend fun getSentences(novelId: Int, chapterId: Int) = api.getSentences(novelId, chapterId)
}
```

- [ ] **Step 5: Create AudioPlayerService.kt**

```kotlin
import android.app.Service
import android.content.Intent
import android.os.IBinder
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem

class AudioPlayerService : Service() {
    private var player: ExoPlayer? = null
    private var currentUrls = listOf<String>()

    fun play(urls: List<String>) {
        currentUrls = urls
        player = ExoPlayer.Builder(this).build()
        player?.setMediaItems(urls.map { MediaItem.fromUri(it) })
        player?.prepare()
        player?.play()
    }

    fun seekToSentence(index: Int) {
        player?.seekTo(index, 0)
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

- [ ] **Step 6: Commit**

```bash
git add android/
git commit -m "feat: add Android client scaffold with API and player"
```

---

### 全部任务概览

| 任务 | 产出 | 可测试 |
|------|------|--------|
| 1 | 项目脚手架 + 数据库模型 | ✅ 单元测试 |
| 2 | 文件解析器 | ✅ 单元测试 |
| 3 | LLM 客户端 | ✅ 集成测试 |
| 4 | 角色分析器 | ✅ 集成测试 |
| 5 | 逐句分析器 | ✅ 集成测试 |
| 6 | 语音库管理 | ✅ 手动验证 |
| 7 | TTS 引擎 + 音频压缩 | ✅ 单元测试 |
| 8 | 管线编排器 | ✅ 端到端 |
| 9 | REST API | ✅ 单元测试 |
| 10 | Web UI | ✅ 手动验证 |
| 11 | 语音库构建 | 手动步骤 |
| 12 | Android 客户端 | 需设备验证 |
