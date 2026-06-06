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
