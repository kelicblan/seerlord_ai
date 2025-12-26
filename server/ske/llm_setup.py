from loguru import logger
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.langchain import LangchainEmbedding
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from typing import Optional

from server.core.config import Settings as CoreSettings
from server.core.config import settings as global_settings
from server.core.llm import get_active_model_config, get_system_setting_value

# Global instances for access by other modules
ske_langchain_llm: Optional[ChatOpenAI] = None
ske_langchain_embeddings: Optional[OpenAIEmbeddings] = None

def initialize_ske_llm():
    """
    Initializes LlamaIndex Settings AND LangChain objects.
    """
    global ske_langchain_llm, ske_langchain_embeddings
    
    core_settings = CoreSettings()
    
    # Avoid re-initialization if already set (optional, but good for testing)
    # However, Settings is a global mutable object, so we just overwrite to be safe.

    # --- 1. Fetch Configuration (DB first, then Env) ---
    llm_db = get_active_model_config("AGENT_LLM_ID")
    emb_db = get_active_model_config("EMBEDDING_MODEL_ID")
    timeout = int(get_system_setting_value("LLM_TIMEOUT", core_settings.LLM_TIMEOUT))

    # --- 2. Configure LLM (LlamaIndex & LangChain) ---
    llm_model_name = core_settings.OPENAI_MODEL
    llm_api_key = core_settings.OPENAI_API_KEY
    llm_base_url = core_settings.OPENAI_API_BASE
    
    if llm_db:
        logger.info(f"SKE: Using DB LLM Configuration: {llm_db.name}")
        llm_model_name = llm_db.model_name
        llm_api_key = llm_db.api_key or "dummy"
        llm_base_url = llm_db.base_url
        if llm_db.provider == "ollama" and not (llm_base_url and llm_base_url.endswith("/v1")):
             # Note: LlamaIndex OpenAILike usually works best with /v1. 
             # If pure Ollama is needed, we might need Ollama class, but OpenAILike is often compatible.
             pass
    else:
        logger.info(f"SKE: Using Env LLM Configuration: {core_settings.LLM_PROVIDER}")

    # LlamaIndex LLM
    Settings.llm = OpenAILike(
        model=llm_model_name,
        api_key=llm_api_key,
        api_base=llm_base_url,
        timeout=timeout,
        max_retries=core_settings.LLM_MAX_RETRIES,
        is_chat_model=True,
    )

    # LangChain LLM
    ske_langchain_llm = ChatOpenAI(
        model=llm_model_name,
        api_key=llm_api_key,
        base_url=llm_base_url,
        temperature=0, # Default to deterministic for extraction
        timeout=timeout,
        max_retries=core_settings.LLM_MAX_RETRIES,
    )

    # --- 3. Configure Embedding ---
    emb_model_name = core_settings.EMBEDDING_MODEL
    emb_api_key = core_settings.EMBEDDINGS_API_KEY or core_settings.OPENAI_API_KEY
    emb_base_url = core_settings.EMBEDDINGS_ENDPOINT or core_settings.OPENAI_API_BASE
    
    if emb_db:
        logger.info(f"SKE: Using DB Embedding Configuration: {emb_db.name}")
        emb_model_name = emb_db.model_name
        emb_api_key = emb_db.api_key or "dummy"
        emb_base_url = emb_db.base_url
    else:
        logger.info(f"SKE: Using Env Embedding Configuration: {core_settings.EMBEDDING_PROVIDER}")

    # Clean base_url
    if emb_base_url and emb_base_url.endswith("/embeddings"):
        emb_base_url = emb_base_url.replace("/embeddings", "")

    lc_embed_model = OpenAIEmbeddings(
        model=emb_model_name,
        openai_api_key=emb_api_key,
        openai_api_base=emb_base_url,
        check_embedding_ctx_length=False,
        timeout=timeout
    )
    
    # Set LlamaIndex global settings
    Settings.embed_model = LangchainEmbedding(lc_embed_model)
    
    # Store LangChain embedding model globally
    ske_langchain_embeddings = lc_embed_model

    logger.info("SKE LLM and Embedding models initialized (LlamaIndex + LangChain).")
