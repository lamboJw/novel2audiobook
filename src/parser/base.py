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
