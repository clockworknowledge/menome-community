from fastapi import APIRouter
from pydantic import BaseModel
from backend.routes import (
    answer_question,
    auth,
    categories,
    explore,
    user,
    file,
    documents,
    notes,
    researcher,
    processing
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(user.router, prefix="/users", tags=["Users"])
api_router.include_router(answer_question.router, prefix="/explore", tags=["Explore"])
api_router.include_router(file.router, prefix="/files", tags=["Files"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(explore.router, prefix="/explore", tags=["Explore"])
api_router.include_router(notes.router, prefix="/notes", tags=["Notes"])
api_router.include_router(researcher.router, prefix="/research", tags=["Research"])
api_router.include_router(processing.router, prefix="/process", tags=["Processing"])
api_router.include_router(categories.router, prefix="/category", tags=["Categories"])
