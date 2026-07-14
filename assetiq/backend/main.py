from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api import routes

app = FastAPI(title="AssetIQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)

if __name__ == "__main__":
    # ❌ WRONG
    # uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
    
    # ✅ CORRECT
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)