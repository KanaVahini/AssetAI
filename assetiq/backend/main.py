"""
FastAPI application entrypoint for AssetIQ backend.
"""

from fastapi import FastAPI
import uvicorn

from api import routes

app = FastAPI()

app.include_router(routes.router)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
