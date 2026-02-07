from fastapi import FastAPI

from src.core.settings import settings
from src.movies.router import router as movies_router

app = FastAPI(title=settings.APP_NAME)

app.include_router(movies_router)
