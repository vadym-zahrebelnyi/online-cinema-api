from fastapi import FastAPI, APIRouter

from src.core.settings import settings

from src.accounts.router import router as accounts_router
from src.orders.routes import router as orders_router

app = FastAPI(title=settings.APP_NAME)

api_router = APIRouter(prefix=settings.API_PREFIX)

for router, prefix, tags in (
        (accounts_router, "/accounts", ["Accounts"]),
        (orders_router, "/orders", ["Orders"]),
):
    api_router.include_router(router, prefix=prefix, tags=tags)

app.include_router(api_router)

