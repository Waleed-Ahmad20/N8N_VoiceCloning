from pydantic import BaseModel
from typing import Optional

class TTSRequest(BaseModel):
    text: str
    voice_id: str
    speed: float = 1.0
    language: str = "EN"

class PDFToSpeechRequest(BaseModel):
    voice_id: str
    speed: float = 1.0
    max_chars: Optional[int] = 5000  # Limit text length for testing