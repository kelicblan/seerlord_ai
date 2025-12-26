from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from server.db.session import get_db
from server.db.models import KnowledgeBase, Document, DocumentStatusEnum, DocumentEvent, DocumentChunk
from server.rag.manager import RAGManager
from pydantic import BaseModel
from loguru import logger
import uuid
import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

router = APIRouter()
rag_manager = RAGManager()

# Pydantic Models
class KBCreate(BaseModel):
    name: str
    description: str | None = None

class KBResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    doc_count: int

    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

class SearchResult(BaseModel):
    text: str
    score: float
    metadata: dict

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    error_msg: str | None
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentEventResponse(BaseModel):
    id: str
    doc_id: str
    event_type: str
    message: str
    data: dict | None
    created_at: datetime

    class Config:
        from_attributes = True

class DocumentChunkResponse(BaseModel):
    point_id: str
    chunk_index: int
    text: str
    text_len: int

class DocumentChunkListResponse(BaseModel):
    items: List[DocumentChunkResponse]

# Endpoints
@router.post("/", response_model=KBResponse)
def create_kb(kb: KBCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    db_kb = KnowledgeBase(
        id=str(uuid.uuid4()),
        name=kb.name,
        description=kb.description
    )
    db.add(db_kb)
    db.commit()
    db.refresh(db_kb)
    background_tasks.add_task(rag_manager.qdrant_service.ensure_collection, kb_id=db_kb.id)
    return KBResponse(
        id=db_kb.id, 
        name=db_kb.name, 
        description=db_kb.description, 
        created_at=db_kb.created_at,
        doc_count=0
    )

@router.get("/", response_model=List[KBResponse])
def list_kbs(db: Session = Depends(get_db)):
    kbs = db.query(KnowledgeBase).all()
    return [
        KBResponse(
            id=kb.id, 
            name=kb.name, 
            description=kb.description, 
            created_at=kb.created_at,
            doc_count=len(kb.documents)
        ) for kb in kbs
    ]

@router.delete("/{kb_id}")
async def delete_kb(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    try:
        await rag_manager.qdrant_service.delete_kb_collection(kb_id)
    except Exception as e:
        logger.error(f"Failed to delete kb collection | kb_id={kb_id} | error={e}")

    db.delete(kb)
    db.commit()
    return {"message": "Knowledge Base deleted"}

@router.post("/{kb_id}/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    kb_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    # Save file
    UPLOAD_DIR = Path("server/data/uploads")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create Document record
    doc_id = str(uuid.uuid4())
    db_doc = Document(
        id=doc_id,
        kb_id=kb_id,
        filename=file.filename,
        file_path=str(file_path.absolute()),
        status=DocumentStatusEnum.PENDING.value
    )
    db.add(db_doc)
    db.commit()

    db.add(
        DocumentEvent(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            event_type="upload_saved",
            message="文件已上传并保存",
            data={"kb_id": kb_id, "filename": file.filename, "file_path": str(file_path.absolute())},
        )
    )
    db.add(
        DocumentEvent(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            event_type="index_enqueued",
            message="索引任务已入队",
            data=None,
        )
    )
    db.commit()

    background_tasks.add_task(rag_manager.process_document, doc_id)

    return {"id": doc_id, "status": "pending", "message": "File uploaded and processing started"}

@router.post("/{kb_id}/search", response_model=List[SearchResult])
async def search_kb(kb_id: str, request: SearchRequest):
    results = await rag_manager.search(request.query, kb_id=kb_id, top_k=request.top_k)
    return results

@router.get("/{kb_id}/documents", response_model=List[DocumentResponse])
def list_documents(kb_id: str, db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.kb_id == kb_id).order_by(Document.created_at.desc()).all()
    return docs

@router.post("/documents/{doc_id}/retry")
def retry_document(doc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc.status = DocumentStatusEnum.PENDING.value
    doc.error_msg = None
    doc.chunk_count = 0
    db.commit()
    db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).delete(synchronize_session=False)
    db.commit()

    db.add(
        DocumentEvent(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            event_type="retry_requested",
            message="用户发起重试",
            data=None,
        )
    )
    db.commit()

    background_tasks.add_task(rag_manager.qdrant_service.delete_document, doc_id, kb_id=doc.kb_id)
    background_tasks.add_task(rag_manager.process_document, doc_id)
    return {"message": "Retry started", "id": doc_id, "status": doc.status}

@router.get("/documents/{doc_id}/events", response_model=List[DocumentEventResponse])
def list_document_events(doc_id: str, db: Session = Depends(get_db)):
    events = (
        db.query(DocumentEvent)
        .filter(DocumentEvent.doc_id == doc_id)
        .order_by(DocumentEvent.created_at.desc())
        .all()
    )
    return events

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/documents/{doc_id}/chunks", response_model=DocumentChunkListResponse)
async def list_document_chunks(
    doc_id: str,
    limit: int = Query(5000, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db_chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.doc_id == doc_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .limit(limit)
        .all()
    )
    if db_chunks:
        return DocumentChunkListResponse(
            items=[
                DocumentChunkResponse(
                    point_id=c.id,
                    chunk_index=c.chunk_index,
                    text=c.text,
                    text_len=c.text_len,
                )
                for c in db_chunks
            ]
        )

    await rag_manager.qdrant_service.ensure_collection(kb_id=doc.kb_id)

    all_points = []
    next_offset = None
    remaining = limit
    while remaining > 0:
        batch_limit = min(200, remaining)
        points, next_offset = await rag_manager.qdrant_service.list_document_chunks(
            doc_id=doc_id,
            kb_id=doc.kb_id,
            limit=batch_limit,
            offset=next_offset,
        )
        all_points.extend(points)
        remaining -= len(points)
        if not next_offset or not points:
            break

    items: List[DocumentChunkResponse] = []
    for p in all_points:
        payload = getattr(p, "payload", None) or {}
        text = payload.get("text") or ""
        items.append(
            DocumentChunkResponse(
                point_id=str(getattr(p, "id", "")),
                chunk_index=int(payload.get("chunk_index") or 0),
                text=text,
                text_len=len(text),
            )
        )

    items.sort(key=lambda x: x.chunk_index)
    return DocumentChunkListResponse(items=items)

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from Qdrant
    await rag_manager.qdrant_service.delete_document(doc_id, kb_id=doc.kb_id)
    
    # Delete from DB
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}
