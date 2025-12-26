import httpx
from server.core.config import settings
from server.core.llm import get_active_model_config
from loguru import logger
from typing import List, Dict, Any, Optional
from urllib.parse import urlsplit

class RAGConnector:
    """
    Handles connections to Embedding and Reranking APIs.
    """

    class EmbeddingAPIError(RuntimeError):
        def __init__(
            self,
            message: str,
            *,
            endpoint: str,
            model: str,
            status_code: int | None = None,
            response_preview: str | None = None,
        ) -> None:
            super().__init__(message)
            self.endpoint = endpoint
            self.model = model
            self.status_code = status_code
            self.response_preview = response_preview

        def to_dict(self) -> Dict[str, Any]:
            return {
                "endpoint": self.endpoint,
                "model": self.model,
                "status_code": self.status_code,
                "response_preview": self.response_preview,
            }

    @staticmethod
    def _safe_endpoint(endpoint: str) -> str:
        try:
            u = urlsplit(endpoint)
            path = u.path or ""
            return f"{u.scheme}://{u.netloc}{path}"
        except Exception:
            return endpoint

    @staticmethod
    def _truncate_text(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[:limit] + "...(truncated)"

    @staticmethod
    def _is_ollama_endpoint(endpoint: str) -> bool:
        ep = (endpoint or "").lower()
        if "11434" in ep:
            return True
        if "/api/embed" in ep or "/api/embeddings" in ep:
            return True
        return False

    @staticmethod
    def _embedding_timeout() -> float:
        try:
            return float(getattr(settings, "EMBEDDINGS_TIMEOUT_SEC"))
        except Exception:
            return 600.0

    @classmethod
    def _parse_embedding_response(cls, *, raw: Any, expected_count: int, endpoint: str, model: str) -> List[List[float]]:
        if isinstance(raw, dict):
            if "data" in raw and isinstance(raw["data"], list):
                return [item["embedding"] for item in raw["data"]]
            if "embeddings" in raw and isinstance(raw["embeddings"], list):
                return raw["embeddings"]
            if "embedding" in raw and isinstance(raw["embedding"], list):
                return [raw["embedding"]]
        raise cls.EmbeddingAPIError(
            "Embedding API returned unexpected response format",
            endpoint=cls._safe_endpoint(str(endpoint)),
            model=model,
            response_preview=cls._truncate_text(str(raw), 1200),
        )

    @classmethod
    def _raise_embedding_error(cls, *, endpoint: str, model: str, err: Exception) -> None:
        safe_endpoint = cls._safe_endpoint(endpoint)

        if isinstance(err, httpx.HTTPStatusError):
            status_code = err.response.status_code if err.response is not None else None
            try:
                body = err.response.text if err.response is not None else ""
            except Exception:
                body = ""
            body_preview = cls._truncate_text(body, 1200) if body else None
            
            msg = f"Embedding API HTTP error ({status_code}) at {safe_endpoint}"
            if body_preview:
                msg += f" | Response: {body_preview}"
                
            raise cls.EmbeddingAPIError(
                msg,
                endpoint=safe_endpoint,
                model=model,
                status_code=status_code,
                response_preview=body_preview,
            ) from err

        if isinstance(err, httpx.TimeoutException):
            raise cls.EmbeddingAPIError(
                f"Embedding API timeout at {safe_endpoint}",
                endpoint=safe_endpoint,
                model=model,
            ) from err

        if isinstance(err, httpx.RequestError):
            raise cls.EmbeddingAPIError(
                f"Embedding API request error at {safe_endpoint}: {type(err).__name__}",
                endpoint=safe_endpoint,
                model=model,
            ) from err

        raise cls.EmbeddingAPIError(
            f"Embedding API unexpected error at {safe_endpoint}: {type(err).__name__}",
            endpoint=safe_endpoint,
            model=model,
        ) from err

    @staticmethod
    def _get_embedding_config():
        """Helper to get embedding config from DB or Env"""
        db_model = get_active_model_config("EMBEDDING_MODEL_ID")
        if db_model:
            endpoint = db_model.base_url
            model = db_model.model_name
            api_key = db_model.api_key
            is_ollama = db_model.provider == "ollama"
            # If provider is openai but base_url not set, assume default?
            # But usually we want explicit base_url for RAGConnector usage
            if not endpoint:
                # Fallback to env default if DB entry is incomplete? 
                # Or just assume standard OpenAI?
                if db_model.provider == "openai":
                    endpoint = "https://api.openai.com/v1/embeddings"
            return endpoint, model, api_key, is_ollama
        
        # Fallback
        endpoint = settings.EMBEDDINGS_ENDPOINT
        model = settings.EMBEDDING_MODEL
        api_key = settings.EMBEDDINGS_API_KEY or settings.OPENAI_API_KEY
        is_ollama = str(getattr(settings, "EMBEDDING_PROVIDER", "")).lower() == "ollama" or RAGConnector._is_ollama_endpoint(endpoint)
        return endpoint, model, api_key, is_ollama

    @staticmethod
    async def get_embedding(text: str) -> List[float]:
        """
        Get embedding for a single text string.
        """
        if not text:
            return []
            
        endpoint, model, api_key, is_ollama = RAGConnector._get_embedding_config()

        async with httpx.AsyncClient() as client:
            try:
                payload: Dict[str, Any] = {"model": model}
                if is_ollama:
                    payload["input"] = text
                else:
                    payload["input"] = text
                    payload["encoding_format"] = "float"

                headers: Dict[str, str] = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = await client.post(endpoint, headers=headers, json=payload, timeout=RAGConnector._embedding_timeout())
                response.raise_for_status()
                raw = response.json()
                vectors = RAGConnector._parse_embedding_response(raw=raw, expected_count=1, endpoint=endpoint, model=model)
                return vectors[0] if vectors else []
            except Exception as e:
                safe_endpoint = RAGConnector._safe_endpoint(str(endpoint))
                logger.opt(exception=True).error(
                    "Embedding failed | endpoint={} | model={} | text_len={} | preview={}",
                    safe_endpoint,
                    model,
                    len(text),
                    RAGConnector._truncate_text(text, 120),
                )
                RAGConnector._raise_embedding_error(endpoint=str(endpoint), model=model, err=e)

    @staticmethod
    async def get_embeddings(texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a list of texts (batch).
        """
        if not texts:
            return []
            
        endpoint, model, api_key, is_ollama = RAGConnector._get_embedding_config()

        async with httpx.AsyncClient() as client:
            try:
                payload: Dict[str, Any] = {"model": model}
                if is_ollama:
                    payload["input"] = texts
                else:
                    payload["input"] = texts
                    payload["encoding_format"] = "float"

                headers: Dict[str, str] = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = await client.post(endpoint, headers=headers, json=payload, timeout=RAGConnector._embedding_timeout())
                response.raise_for_status()
                raw = response.json()
                vectors = RAGConnector._parse_embedding_response(raw=raw, expected_count=len(texts), endpoint=endpoint, model=model)
                return vectors
            except Exception as e:
                safe_endpoint = RAGConnector._safe_endpoint(str(endpoint))
                first_preview = texts[0] if texts else ""
                logger.opt(exception=True).error(
                    "Batch embedding failed | endpoint={} | model={} | texts_count={} | first_len={} | first_preview={}",
                    safe_endpoint,
                    model,
                    len(texts),
                    len(first_preview),
                    RAGConnector._truncate_text(first_preview, 120),
                )
                RAGConnector._raise_embedding_error(endpoint=str(endpoint), model=model, err=e)

    @staticmethod
    async def rerank(query: str, documents: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank documents using the configured Reranker.
        Expected API format: JSON POST with query, documents, model, top_n.
        """
        # Get Config
        db_model = get_active_model_config("RERANKER_MODEL_ID")
        if db_model:
            endpoint = db_model.base_url
            model = db_model.model_name
            api_key = db_model.api_key
        else:
            endpoint = settings.RERANKER_ENDPOINT
            model = settings.RERANKER_MODEL
            api_key = settings.EMBEDDINGS_API_KEY or settings.OPENAI_API_KEY

        if not endpoint:
            logger.warning("No RERANKER_ENDPOINT configured. Skipping rerank.")
            return [{"index": i, "relevance_score": 0.0, "text": doc} for i, doc in enumerate(documents[:top_n])]

        async with httpx.AsyncClient() as client:
            try:
                # Construct payload compatible with typical Rerank APIs (e.g. Jina, Cohere, BGE-M3 wrapper)
                payload = {
                    "query": query,
                    "documents": documents,
                    "model": model,
                    "top_n": top_n
                }
                
                headers = {
                    "Content-Type": "application/json"
                }
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Handle different response formats
                # Format 1: { "results": [ {"index": 0, "relevance_score": 0.9}, ... ] }
                if "results" in result:
                    return result["results"]
                # Format 2: List directly
                elif isinstance(result, list):
                    return result
                
                logger.warning(f"Unknown reranker response format: {result.keys()}")
                return [{"index": i, "relevance_score": 0.0} for i in range(len(documents))]
                
            except Exception as e:
                logger.error(f"Reranking failed: {e}")
                # Fallback: return indices as is
                return [{"index": i, "relevance_score": 0.0} for i in range(min(len(documents), top_n))]
