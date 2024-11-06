
from pydantic import BaseModel
from typing import List


class GenerateResearchRequest(BaseModel):
    topics: List[str]
    
