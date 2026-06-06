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
