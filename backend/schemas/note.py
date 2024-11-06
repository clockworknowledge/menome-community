from pydantic import BaseModel
from typing import Optional, List
from backend.schemas.file import OpenAIFile


class NotePayload(BaseModel):
    name: str
    note_text: str
    openaiFileIdRefs: Optional[List[OpenAIFile]] = None

class NoteResponse(BaseModel):
    id: str
    name: str
    note_text: str
    files: List[str]

class NoteCreate(BaseModel):
    content: str
    documentid: str