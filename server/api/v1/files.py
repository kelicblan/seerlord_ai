from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
import uuid
from loguru import logger
from pathlib import Path

router = APIRouter()

# Define upload directory
REPO_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_DIR = (REPO_ROOT / "server" / "data" / "uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file to the server.
    Returns the absolute file path.
    """
    try:
        # Generate unique filename to avoid collisions while keeping extension
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = (UPLOAD_DIR / unique_filename).resolve()
        
        logger.info(f"Uploading file: {original_filename} to {file_path}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "filename": original_filename,
            "saved_filename": unique_filename,
            "file_path": str(file_path)
        }
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
