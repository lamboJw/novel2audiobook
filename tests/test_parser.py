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


def test_txt_parser_sentence_splitting():
    text = "你好！你叫什么？我叫张三。\n嗯。"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        parser = TxtParser()
        chapters = parser.parse(path)
        sentences = chapters[0].sentences
        assert len(sentences) == 4
        assert sentences[0] == "你好！"
        assert sentences[1] == "你叫什么？"
        assert sentences[2] == "我叫张三。"
    finally:
        os.unlink(path)
