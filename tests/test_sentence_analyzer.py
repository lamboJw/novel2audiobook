import json
from src.llm.sentence_analyzer import SentenceAnalyzer
from src.database import SessionLocal, init_db
from src.models import Novel, Chapter


def test_split_sentences():
    db = SessionLocal()
    try:
        sa = SentenceAnalyzer(None, db)
        result = sa._split_sentences("你好。你叫什么？我叫张三。\n嗯。")
        assert len(result) == 4
        assert result[0] == "你好。"
        assert result[1] == "你叫什么？"
        assert result[2] == "我叫张三。"
        assert result[3] == "嗯。"
    finally:
        db.close()


def test_split_sentences_empty():
    db = SessionLocal()
    try:
        sa = SentenceAnalyzer(None, db)
        result = sa._split_sentences("")
        assert result == []
    finally:
        db.close()


def test_parse_result():
    db = SessionLocal()
    try:
        sa = SentenceAnalyzer(None, db)
        lines = "0|张三|高兴\n1|旁白|平静"
        sentences = ["你好吗？", "他笑了。"]
        result = sa._parse_result(lines, sentences, 0)
        assert len(result) == 2
        assert result[0]["speaker"] == "张三"
        assert result[0]["emotion"] == "高兴"
        assert result[1]["speaker"] == "旁白"
        assert result[1]["emotion"] == "平静"
        assert json.loads(result[1]["emotion_vector"]) == [0, 0, 0, 0, 0, 0, 0, 1.0]
    finally:
        db.close()


def test_parse_result_filters_invalid():
    db = SessionLocal()
    try:
        sa = SentenceAnalyzer(None, db)
        lines = "99|张三|高兴"
        sentences = ["只有一句。"]
        result = sa._parse_result(lines, sentences, 0)
        assert len(result) == 0
    finally:
        db.close()
