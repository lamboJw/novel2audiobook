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
