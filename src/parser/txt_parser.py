import re
from src.parser.base import NovelParser, Chapter, SENTENCE_RE

CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千零0-9]+章.*$", re.MULTILINE)


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
