from fastapi import FastAPI
from src.orders.routes import router as orders_router

from src.core.settings import settings

app = FastAPI(title=settings.APP_NAME)

app.include_router(orders_router, prefix=f"{settings.API_PREFIX}/orders", tags=["Orders"])
