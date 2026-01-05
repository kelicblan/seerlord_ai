from typing import Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_ollama import ChatOllama, OllamaEmbeddings
from server.core.config import settings
from loguru import logger
from server.db.session import SessionLocal
from server.db.models import SystemSetting, LLMModel

def get_active_model_config(setting_key: str):
    """
    Retrieve the active model configuration from the database.
    Returns None if not configured or not found.
    """
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == setting_key).first()
        if not setting:
            return None
        
        try:
            model_id = int(setting.value)
        except ValueError:
            return None
            
        model = db.query(LLMModel).filter(LLMModel.id == model_id).first()
        return model
    except Exception as e:
        logger.error(f"Error fetching active model config for {setting_key}: {e}")
        return None
    finally:
        db.close()

def get_system_setting_value(key: str, default=None):
    db = SessionLocal()
    try:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        return setting.value if setting else default
    except Exception:
        return default
    finally:
        db.close()

def get_embeddings():
    """
    Factory function to get the configured Embeddings instance.
    """
    # Try DB first
    db_model = get_active_model_config("EMBEDDING_MODEL_ID")
    timeout = int(get_system_setting_value("LLM_TIMEOUT", settings.LLM_TIMEOUT))
    
    if db_model:
        provider = db_model.provider
        base_url = db_model.base_url
        api_key = db_model.api_key
        model_name = db_model.model_name
        
        if provider == "openai":
            # Clean base_url if it ends with /embeddings
            if base_url and base_url.endswith("/embeddings"):
                base_url = base_url[:-11]
            
            return OpenAIEmbeddings(
                api_key=api_key or "dummy",
                base_url=base_url,
                model=model_name,
                timeout=timeout,
                max_retries=settings.LLM_MAX_RETRIES,
                check_embedding_ctx_length=False,
            )
        elif provider == "ollama":
             # Clean up base_url
            if base_url:
                if "/api/embed" in base_url:
                    base_url = base_url.split("/api/embed")[0]
                elif "/v1" in base_url:
                    base_url = base_url.split("/v1")[0]
            
            return OllamaEmbeddings(
                base_url=base_url,
                model=model_name
            )

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
        base_url = settings.EMBEDDINGS_ENDPOINT or settings.OLLAMA_BASE_URL
        # Clean up base_url for OllamaEmbeddings which expects root url
        if base_url:
            if "/api/embed" in base_url:
                base_url = base_url.split("/api/embed")[0]
            elif "/v1" in base_url:
                base_url = base_url.split("/v1")[0]

        return OllamaEmbeddings(
            base_url=base_url,
            model=settings.EMBEDDING_MODEL
        )
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")

def get_llm(temperature: float = 0.7, model: Optional[str] = None, use_full_modal: bool = False):
    """
    Factory function to get the configured LLM instance based on settings.
    
    Args:
        temperature: Sampling temperature.
        model: Optional override for the model name.
        use_full_modal: If True, use FULL_MODAL_MODEL_ID instead of AGENT_LLM_ID
    """
    setting_key = "FULL_MODAL_MODEL_ID" if use_full_modal else "AGENT_LLM_ID"
    db_model = get_active_model_config(setting_key)
    # If full modal requested but not configured, fallback to default agent LLM
    if use_full_modal and not db_model:
        db_model = get_active_model_config("AGENT_LLM_ID")

    timeout = int(get_system_setting_value("LLM_TIMEOUT", settings.LLM_TIMEOUT))

    if db_model:
        provider = db_model.provider
        base_url = db_model.base_url
        api_key = db_model.api_key
        model_name = model or db_model.model_name
        
        if provider == "openai":
             return ChatOpenAI(
                api_key=api_key or "dummy",
                base_url=base_url,
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                max_retries=settings.LLM_MAX_RETRIES
            )
        elif provider == "ollama":
             # 智能检测：如果 OLLAMA_BASE_URL 是 OpenAI 兼容格式 (/v1)，则使用 ChatOpenAI 客户端
             if base_url and base_url.endswith("/v1"):
                logger.info(f"Detected OpenAI-compatible Ollama endpoint from DB: {base_url}")
                return ChatOpenAI(
                    api_key="ollama",
                    base_url=base_url,
                    model=model_name,
                    temperature=temperature,
                    timeout=timeout,
                    max_retries=settings.LLM_MAX_RETRIES
                )
             else:
                return ChatOllama(
                    base_url=base_url,
                    model=model_name,
                    temperature=temperature,
                    timeout=timeout
                )
    
    # Fallback to env vars
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
