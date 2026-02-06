from fastapi import FastAPI
from src.accounts.router import router as accounts_router
app = FastAPI()


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}



app.include_router(
    accounts_router,
    prefix="/accounts",
    tags=["Accounts"]
)