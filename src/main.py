from fastapi import FastAPI
from src.movies.router import router as movies_router

app = FastAPI(title="Online Cinema API")

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

app.include_router(movies_router)
