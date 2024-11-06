from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime
from backend.config import ValidTypes

class QuestionRequest(BaseModel):
    query: str
    
class FindRequest(BaseModel):
    query: str

class DocumentRequest(BaseModel):
    url: HttpUrl
    note: Optional[str] = None

class DocumentResponse(BaseModel):
    uuid: str
    name: str
    url: HttpUrl
    text: str
    imageurl: str
    publisher: str
    addeddate: str
    thumbnail: str
    wordcount: int


class DocumentFindInput(BaseModel):
    start_date: Optional[datetime] = Field(
        description="Minimum publication year of the document"
    )
    end_date: Optional[datetime] = Field(
        description="Maximum publication year of the document"
    )
    document_type: Optional[ValidTypes] = Field(description="Type of the document")
    grouping_key: Optional[str] = Field(
        description="The key to group by the aggregation",
        json_schema_extra={"enum": ["year"]}
    )


class DocumentListInput(BaseModel):
    sort_by: str = Field(
        description="How to sort documents, can be one of either latest, name",
        json_schema_extra={"enum": ['latest', 'name']}
    )
    k: Optional[int] = Field(description="Number of documents to return")
    description: Optional[str] = Field(description="Description of the document")
    start_date: Optional[str] = Field(description="Minimum publication date of the document in the format YYYY-MM-DD")
    end_date: Optional[str] = Field(description="Maximum publication date of the document in the format YYYY-MM-DD")
    document_type: Optional[str] = Field(
        description=f"Type of the document can be one of the ValidTypes: {', '.join([str(vt) for vt in ValidTypes])}",
        json_schema_extra={"enum": [str(vt) for vt in ValidTypes]}
    )

