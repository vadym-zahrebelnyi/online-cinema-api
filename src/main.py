from fastapi import FastAPI

from src.core.settings import settings
from src.accounts.router import router as accounts_router
from src.orders.routes import router as orders_router

app = FastAPI(title=settings.APP_NAME)

app.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
app.include_router(
    orders_router, prefix=f"{settings.API_PREFIX}/orders", tags=["Orders"]
)
