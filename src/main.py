from fastapi import FastAPI, APIRouter

from src.core.settings import settings

from src.accounts.router import router as accounts_router
from src.orders.routes import router as orders_router

app = FastAPI(title=settings.APP_NAME)
from fastapi import FastAPI
from src.movies.router import router as movies_router

app = FastAPI(title="Online Cinema API")

app.include_router(api_router)

app.include_router(movies_router)
