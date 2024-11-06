from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from fastapi import UploadFile


class OpenAIFile(BaseModel):
    name: str
    id: str
    mime_type: Optional[str] = Field(None, description="MIME type of the file")
    download_link: str



# multi-part file upload    
class FileUpload(BaseModel):
    file: UploadFile
    content_type: Optional[str] = None
    note_text: Optional[str] = None
    size: Optional[int] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

