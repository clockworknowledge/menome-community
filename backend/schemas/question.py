from pydantic import BaseModel

# Add typing for input
class Question(BaseModel):
    question: str