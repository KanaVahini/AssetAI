import os
import sys

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
import shutil

# Direct imports using full paths — no confusion
sys.path.append(os.path.abspath("backend/agents/copilot"))
sys.path.append(os.path.abspath("backend/agents/rca"))
sys.path.append(os.path.abspath("backend/rag"))

import copilot_agent
import rca_agent

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    plant_name: str = None


class RCARequest(BaseModel):
    equipment_tag: str


@router.get("/")
def home():
    return {"status": "AssetIQ is running", "version": "1.0"}


@router.post("/ask")
def ask_question(request: QueryRequest):
    result = copilot_agent.run(
        user_query=request.question,
        plant_name=request.plant_name
    )
    return result


@router.post("/rca")
def run_rca(request: RCARequest):
    report = rca_agent.run(request.equipment_tag)
    return report


@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    save_path = f"data/raw/{file.filename}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": f"Uploaded {file.filename} successfully"}


@router.get("/health")
def health_check():
    return {"status": "healthy"}