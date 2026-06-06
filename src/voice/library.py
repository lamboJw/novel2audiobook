import json
from sqlalchemy.orm import Session
from src.models import VoiceLibrary


class VoiceLibraryManager:
    def __init__(self, db: Session):
        self.db = db

    def load_metadata(self, metadata_path: str):
        with open(metadata_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            existing = self.db.query(VoiceLibrary).filter_by(name=entry["name"]).first()
            if existing:
                for k, v in entry.items():
                    setattr(existing, k, v)
            else:
                self.db.add(VoiceLibrary(**entry))
        self.db.commit()

    def get_entry(self, voice_ref_id: int) -> VoiceLibrary:
        return self.db.get(VoiceLibrary, voice_ref_id)

    def list_all(self, gender: str = None, age_group: str = None) -> list[VoiceLibrary]:
        q = self.db.query(VoiceLibrary)
        if gender:
            q = q.filter_by(gender=gender)
        if age_group:
            q = q.filter_by(age_group=age_group)
        return q.all()
