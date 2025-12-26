from sqlalchemy.orm import Session
from server.db.session import SessionLocal
from server.db.models import Document, DocumentStatusEnum, DocumentEvent, DocumentChunk
from server.rag.ingest import IngestionService
from server.rag.connector import RAGConnector
from server.rag.qdrant import QdrantService
from loguru import logger
import asyncio
import time
import uuid
from server.core.config import settings
from server.core.llm import get_active_model_config

class RAGManager:
    def __init__(self):
        self.ingest_service = IngestionService()
        self.qdrant_service = QdrantService()
        self.connector = RAGConnector()

    @staticmethod
    def _error_summary(err: Exception) -> str:
        msg = str(err).strip()
        if msg:
            return f"{type(err).__name__}: {msg}"
        return f"{type(err).__name__}: {repr(err)}"

    async def process_document(self, doc_id: str):
        """
        Background task to process a document.
        Creates its own DB session to avoid detached instance issues.
        """
        logger.info(f"Starting processing for doc_id: {doc_id}")
        db = SessionLocal()
        try:
            def add_event(event_type: str, message: str, data: dict | None = None) -> None:
                db.add(
                    DocumentEvent(
                        id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        event_type=event_type,
                        message=message,
                        data=data,
                    )
                )
                db.commit()

            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                logger.error(f"Document {doc_id} not found")
                return

            # Resolve embedding config for logging
            emb_conf = get_active_model_config("EMBEDDING_MODEL_ID")
            emb_model_name = emb_conf.model_name if emb_conf else settings.EMBEDDING_MODEL
            emb_endpoint_url = emb_conf.base_url if emb_conf else settings.EMBEDDINGS_ENDPOINT

            # Update status to INDEXING
            doc.status = DocumentStatusEnum.INDEXING.value
            db.commit()
            add_event(
                "index_start",
                "开始索引",
                {
                    "kb_id": doc.kb_id,
                    "filename": doc.filename,
                    "status": doc.status,
                    "progress": 0.05,
                    "pipeline": {
                        "chunk_size": getattr(self.ingest_service.splitter, "chunk_size", None),
                        "chunk_overlap": getattr(self.ingest_service.splitter, "chunk_overlap", None),
                        "embedding_model": emb_model_name,
                        "embedding_endpoint": emb_endpoint_url,
                        "qdrant_collection": self.qdrant_service.get_collection_name(doc.kb_id),
                    },
                },
            )

            try:
                # 1. Parse
                add_event("parse_start", "开始解析文件", {"file_path": doc.file_path, "progress": 0.1})
                logger.info(f"Parsing file: {doc.file_path}")
                t0 = time.perf_counter()
                text = self.ingest_service.parse_file(doc.file_path)
                add_event("parse_done", "文件解析完成", {"elapsed_ms": int((time.perf_counter() - t0) * 1000), "text_len": len(text), "progress": 0.2})
                
                # 2. Chunk
                add_event(
                    "chunk_start",
                    "开始切分文本",
                    {
                        "chunk_size": getattr(self.ingest_service.splitter, "chunk_size", None),
                        "chunk_overlap": getattr(self.ingest_service.splitter, "chunk_overlap", None),
                        "separators": getattr(self.ingest_service.splitter, "separators", None),
                        "progress": 0.25,
                    },
                )
                logger.info("Chunking text...")
                t0 = time.perf_counter()
                chunks = self.ingest_service.chunk_text(text)
                chunk_lens = [len(c) for c in chunks]
                add_event(
                    "chunk_done",
                    "文本切分完成",
                    {
                        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                        "chunk_count": len(chunks),
                        "chunk_len_min": min(chunk_lens) if chunk_lens else 0,
                        "chunk_len_max": max(chunk_lens) if chunk_lens else 0,
                        "chunk_len_avg": int(sum(chunk_lens) / len(chunk_lens)) if chunk_lens else 0,
                        "progress": 0.35,
                    },
                )
                try:
                    db.query(DocumentChunk).filter(DocumentChunk.doc_id == doc_id).delete(synchronize_session=False)
                    for i, chunk_text in enumerate(chunks):
                        db.add(
                            DocumentChunk(
                                id=str(uuid.uuid4()),
                                doc_id=doc_id,
                                chunk_index=i,
                                text=chunk_text,
                                text_len=len(chunk_text),
                            )
                        )
                    doc.chunk_count = len(chunks)
                    db.commit()
                    add_event("chunk_persisted", "切片已持久化", {"chunk_count": len(chunks), "progress": 0.38})
                except Exception as e:
                    logger.error(f"Failed to persist chunks for document {doc_id}: {e}")
                    add_event("chunk_persist_failed", "切片持久化失败", {"error": str(e), "progress": 0.38})
                if not chunks:
                    logger.warning("No chunks generated from file.")
                
                # 3. Embed
                add_event(
                    "embed_start",
                    "开始向量化",
                    {"model": emb_model_name, "chunk_count": len(chunks), "endpoint": emb_endpoint_url, "progress": 0.4},
                )
                logger.info(f"Generating embeddings for {len(chunks)} chunks...")
                t0 = time.perf_counter()
                embed_provider = emb_conf.provider if emb_conf else str(getattr(settings, "EMBEDDING_PROVIDER", "openai")).lower()
                # 1. Determine batch size
                configured_batch_size = int(getattr(settings, "EMBEDDINGS_BATCH_SIZE", 128))
                endpoint = str(emb_endpoint_url or "").lower()
                
                # Special handling for DashScope/Aliyun which has a limit of 10
                if "dashscope" in endpoint or "aliyun" in endpoint:
                     embed_batch_size = max(1, min(configured_batch_size, 10))
                elif embed_provider == "ollama":
                    embed_batch_size = max(1, min(configured_batch_size, 128))
                else:
                    embed_batch_size = max(1, min(configured_batch_size, 2048))
                embeddings: list[list[float]] = []
                total_batches = (len(chunks) + embed_batch_size - 1) // embed_batch_size if chunks else 0
                for bi in range(total_batches):
                    start = bi * embed_batch_size
                    end = min(len(chunks), start + embed_batch_size)
                    add_event(
                        "embed_batch_start",
                        "向量化批次开始",
                        {"batch_index": bi + 1, "total_batches": total_batches, "batch_size": end - start, "progress": 0.4},
                    )
                    bt0 = time.perf_counter()
                    try:
                        batch_embeddings = await self.connector.get_embeddings(chunks[start:end])
                    except Exception as e:
                        error_data: dict = {
                            "batch_index": bi + 1,
                            "total_batches": total_batches,
                            "batch_size": end - start,
                            "chunk_range": [start, end],
                            "model": emb_model_name,
                            "endpoint": str(emb_endpoint_url),
                            "error": self._error_summary(e),
                        }
                        if isinstance(e, getattr(RAGConnector, "EmbeddingAPIError", ())):
                            try:
                                error_data.update(getattr(e, "to_dict")())
                            except Exception:
                                pass
                        add_event("embed_batch_failed", "向量化批次失败", error_data)
                        raise
                    embeddings.extend(batch_embeddings)
                    add_event(
                        "embed_batch_done",
                        "向量化批次完成",
                        {
                            "batch_index": bi + 1,
                            "total_batches": total_batches,
                            "batch_size": end - start,
                            "elapsed_ms": int((time.perf_counter() - bt0) * 1000),
                            "embedded_total": len(embeddings),
                            "progress": 0.4 + (0.25 * ((bi + 1) / max(total_batches, 1))),
                        },
                    )
                add_event(
                    "embed_done",
                    "向量化完成",
                    {"elapsed_ms": int((time.perf_counter() - t0) * 1000), "vector_count": len(embeddings), "batch_size": embed_batch_size, "progress": 0.65},
                )
                
                # 4. Store in Qdrant
                add_event(
                    "vector_store_start",
                    "开始写入向量库",
                    {"collection": self.qdrant_service.get_collection_name(doc.kb_id)},
                )
                logger.info("Upserting to Qdrant...")
                t0 = time.perf_counter()
                
                # Determine dimension from embeddings to ensure collection matches model
                dim = len(embeddings[0]) if embeddings and len(embeddings) > 0 else None
                await self.qdrant_service.ensure_collection(kb_id=doc.kb_id, vector_size=dim)

                add_event(
                    "vector_store_collection_ready",
                    "向量库集合就绪",
                    {"collection": self.qdrant_service.get_collection_name(doc.kb_id), "progress": 0.7},
                )

                async def _on_qdrant_progress(payload: dict) -> None:
                    phase = payload.get("phase")
                    if phase == "upsert_batch_start":
                        add_event(
                            "vector_store_batch_start",
                            "写入批次开始",
                            {
                                "batch_index": payload.get("batch_index"),
                                "total_batches": payload.get("total_batches"),
                                "batch_size": payload.get("batch_size"),
                                "total_points": payload.get("total_points"),
                                "progress": 0.7,
                            },
                        )
                    elif phase == "upsert_batch_done":
                        total_batches_local = int(payload.get("total_batches") or 1)
                        batch_index_local = int(payload.get("batch_index") or 1)
                        add_event(
                            "vector_store_batch_done",
                            "写入批次完成",
                            {
                                "batch_index": batch_index_local,
                                "total_batches": total_batches_local,
                                "batch_size": payload.get("batch_size"),
                                "total_points": payload.get("total_points"),
                                "progress": 0.7 + (0.25 * (batch_index_local / max(total_batches_local, 1))),
                            },
                        )

                await self.qdrant_service.upsert_documents(
                    kb_id=doc.kb_id,
                    doc_id=doc.id,
                    chunks=chunks,
                    embeddings=embeddings,
                    progress_cb=_on_qdrant_progress,
                )
                add_event("vector_store_done", "向量库写入完成", {"elapsed_ms": int((time.perf_counter() - t0) * 1000), "chunk_count": len(chunks)})

                # Update status to COMPLETED
                doc.status = DocumentStatusEnum.COMPLETED.value
                doc.chunk_count = len(chunks)
                doc.error_msg = None
                db.commit()
                add_event("index_done", "索引完成", {"status": doc.status, "chunk_count": doc.chunk_count})
                logger.info(f"Document {doc_id} processed successfully")

            except Exception as e:
                logger.opt(exception=True).error(
                    "Failed to process document {} | error={}",
                    doc_id,
                    self._error_summary(e),
                )
                # Re-query doc to ensure it's attached
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.status = DocumentStatusEnum.FAILED.value
                    doc.error_msg = self._error_summary(e)
                    db.commit()
                    add_event("index_failed", "索引失败", {"status": doc.status, "error": doc.error_msg})
        
        except Exception as e:
            logger.opt(exception=True).critical("Critical error in process_document | doc_id={} | error={}", doc_id, self._error_summary(e))
            try:
                db.add(
                    DocumentEvent(
                        id=str(uuid.uuid4()),
                        doc_id=doc_id,
                        event_type="index_failed",
                        message="索引失败",
                        data={"error": str(e)},
                    )
                )
                db.commit()
            except Exception:
                pass
        finally:
            db.close()

    async def search(self, query: str, kb_id: str = None, top_k: int = 5):
        """
        End-to-end search: Embed -> Vector Search -> Rerank
        """
        # 1. Embed Query
        query_vector = await self.connector.get_embedding(query)
        
        # 2. Vector Search (Get top 50 candidates)
        candidates = await self.qdrant_service.search(
            query_vector=query_vector,
            kb_id=kb_id,
            limit=50
        )
        
        if not candidates:
            return []

        # Extract texts for reranking
        candidate_texts = [point.payload["text"] for point in candidates]
        
        # 3. Rerank
        logger.info(f"Reranking {len(candidate_texts)} candidates...")
        reranked_results = await self.connector.rerank(
            query=query,
            documents=candidate_texts,
            top_n=top_k
        )
        
        # Merge results
        final_results = []
        for res in reranked_results:
            idx = res.get("index")
            score = res.get("relevance_score")
            # Map back to original candidate
            if idx is not None and idx < len(candidates):
                candidate = candidates[idx]
                final_results.append({
                    "text": candidate.payload["text"],
                    "score": score,
                    "metadata": {
                        "doc_id": candidate.payload.get("doc_id"),
                        "chunk_index": candidate.payload.get("chunk_index"),
                        "kb_id": candidate.payload.get("kb_id")
                    }
                })
        
        # Sort by score just in case
        final_results.sort(key=lambda x: x["score"], reverse=True)
        return final_results
