from typing import Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from server.core.config import settings
from loguru import logger

def get_embeddings():
    """
    Factory function to get the configured Embeddings instance.
    """
    if settings.EMBEDDING_PROVIDER == "openai":
        api_key = settings.EMBEDDINGS_API_KEY or settings.OPENAI_API_KEY
        base_url = settings.EMBEDDINGS_ENDPOINT or settings.OPENAI_API_BASE
        
        # Clean base_url if it ends with /embeddings
        if base_url and base_url.endswith("/embeddings"):
            base_url = base_url[:-11]

        if not api_key:
             raise ValueError("API Key is required for OpenAI embeddings")
        
        return OpenAIEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=settings.EMBEDDING_MODEL,
            timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
            check_embedding_ctx_length=False,
        )
    elif settings.EMBEDDING_PROVIDER == "ollama":
        return OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.EMBEDDING_MODEL
        )
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")

def get_llm(temperature: float = 0.7, model: Optional[str] = None):
    """
    Factory function to get the configured LLM instance based on settings.
    
    Args:
        temperature: Sampling temperature.
        model: Optional override for the model name.
    """
    if settings.LLM_PROVIDER == "openai":
        if not settings.OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is missing but LLM_PROVIDER is 'openai'")
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
            
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            model=model or settings.OPENAI_MODEL,
            temperature=temperature,
            timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES
        )
    elif settings.LLM_PROVIDER == "ollama":
        # 智能检测：如果 OLLAMA_BASE_URL 是 OpenAI 兼容格式 (/v1)，则使用 ChatOpenAI 客户端
        if settings.OLLAMA_BASE_URL.endswith("/v1"):
            logger.info(f"Detected OpenAI-compatible Ollama endpoint: {settings.OLLAMA_BASE_URL}")
            return ChatOpenAI(
                api_key="ollama",  # Ollama 通常忽略 API Key
                base_url=settings.OLLAMA_BASE_URL,
                model=model or settings.OLLAMA_MODEL,
                temperature=temperature,
                timeout=settings.LLM_TIMEOUT,
                max_retries=settings.LLM_MAX_RETRIES
            )
        else:
            return ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=model or settings.OLLAMA_MODEL,
                temperature=temperature,
                timeout=settings.LLM_TIMEOUT,
                # ChatOllama does not have max_retries param in init, usually handled by invoke retry
            )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
