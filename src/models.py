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
