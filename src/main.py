from fastapi import APIRouter, FastAPI

from src.accounts.router import router as accounts_router
from src.core.settings import settings
from src.movies.router import router as movies_router
from src.orders.routes import router as orders_router
from src.payments.pages.router import router as payment_pages_router
from src.payments.router import router as payments_router

app = FastAPI(title=settings.APP_NAME)

api_router = APIRouter(prefix=settings.API_PREFIX)

for router, prefix, tags in (
    (accounts_router, "/accounts", ["Accounts"]),
    (orders_router, "/orders", ["Orders"]),
    (payments_router, "/payments", ["Payments"]),
    (movies_router, "/movies", ["Movies"]),
):
    api_router.include_router(router, prefix=prefix, tags=tags)

app.include_router(api_router)
app.include_router(payment_pages_router, tags=["Pages"])
