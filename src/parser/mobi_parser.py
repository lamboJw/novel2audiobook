import shutil
import tempfile
import os
from src.parser.base import NovelParser, Chapter
from src.parser.txt_parser import TxtParser


class MobiParser(NovelParser):
    def parse(self, path: str) -> list[Chapter]:
        try:
            import mobi
            temp_dir = tempfile.mkdtemp()
            try:
                _, filepath = mobi.extract(path, temp_dir)
                epub_path = None
                for f in os.listdir(filepath):
                    if f.endswith(".epub") or f.endswith(".html"):
                        epub_path = os.path.join(filepath, f)
                        break
                if epub_path and epub_path.endswith(".epub"):
                    from src.parser.epub_parser import EpubParser
                    parser = EpubParser()
                    return parser.parse(epub_path)
                elif epub_path:
                    parser = TxtParser()
                    return parser.parse(epub_path)
                else:
                    raise ValueError("Could not extract content from MOBI")
            finally:
                shutil.rmtree(temp_dir)
        except ImportError:
            raise ImportError("mobi package not available. Install with: uv pip install mobi")
