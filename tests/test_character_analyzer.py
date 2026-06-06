import pytest
from src.llm.client import LLMClient
from src.llm.character_analyzer import CharacterAnalyzer
from src.database import SessionLocal, init_db
from src.models import Novel
import os


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
        has_zhangsan = "张三" in names
        has_wangwu = "王五" in names
        assert has_zhangsan or has_wangwu
    finally:
        session.close()
