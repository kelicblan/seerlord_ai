import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from server.db.session import SessionLocal
from server.db.models import LLMModel, SystemSetting
from dotenv import load_dotenv

def migrate():
    # Load .env manually to ensure we get the file content
    env_path = project_root / ".env"
    load_dotenv(env_path)
    
    db = SessionLocal()
    try:
        print("Starting migration...")
        
        # 1. Parse .env values
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_model_name = os.getenv("OPENAI_MODEL")
        openai_base_url = os.getenv("OPENAI_API_BASE")
        
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        ollama_model_name = os.getenv("OLLAMA_MODEL")
        
        emb_endpoint = os.getenv("EMBEDDINGS_ENDPOINT")
        emb_model_name = os.getenv("EMBEDDINGS_MODEL")
        emb_api_key = os.getenv("EMBEDDINGS_API_KEY")
        
        rerank_endpoint = os.getenv("RERANKER_ENDPOINT")
        rerank_model_name = os.getenv("RERANKER_MODEL")
        rerank_api_key = os.getenv("RERANKER_API_KEY")
        
        llm_timeout = os.getenv("LLM_TIMEOUT", "120")
        active_provider = os.getenv("LLM_PROVIDER", "openai")

        # 2. Create Models
        
        # OpenAI LLM
        openai_llm = None
        if openai_model_name:
            openai_llm = db.query(LLMModel).filter(LLMModel.name == "OpenAI (Env)").first()
            if not openai_llm:
                openai_llm = LLMModel(
                    name="OpenAI (Env)",
                    provider="openai",
                    model_name=openai_model_name,
                    base_url=openai_base_url,
                    api_key=openai_api_key,
                    model_type="llm"
                )
                db.add(openai_llm)
                db.flush() # Get ID
                print(f"Created OpenAI model with ID: {openai_llm.id}")
        
        # Ollama LLM
        ollama_llm = None
        if ollama_model_name:
            ollama_llm = db.query(LLMModel).filter(LLMModel.name == "Ollama (Env)").first()
            if not ollama_llm:
                ollama_llm = LLMModel(
                    name="Ollama (Env)",
                    provider="ollama",
                    model_name=ollama_model_name,
                    base_url=ollama_base_url,
                    model_type="llm"
                )
                db.add(ollama_llm)
                db.flush()
                print(f"Created Ollama model with ID: {ollama_llm.id}")

        # Embedding
        emb_model = None
        if emb_model_name:
            emb_model = db.query(LLMModel).filter(LLMModel.name == "Embedding (Env)").first()
            if not emb_model:
                emb_model = LLMModel(
                    name="Embedding (Env)",
                    provider="openai", # Assuming compatible API
                    model_name=emb_model_name,
                    base_url=emb_endpoint,
                    api_key=emb_api_key,
                    model_type="embedding"
                )
                db.add(emb_model)
                db.flush()
                print(f"Created Embedding model with ID: {emb_model.id}")

        # Reranker
        rerank_model = None
        if rerank_model_name:
            rerank_model = db.query(LLMModel).filter(LLMModel.name == "Reranker (Env)").first()
            if not rerank_model:
                rerank_model = LLMModel(
                    name="Reranker (Env)",
                    provider="openai", # Assuming compatible API
                    model_name=rerank_model_name,
                    base_url=rerank_endpoint,
                    api_key=rerank_api_key,
                    model_type="reranker"
                )
                db.add(rerank_model)
                db.flush()
                print(f"Created Reranker model with ID: {rerank_model.id}")

        # 3. Create System Settings
        
        # AGENT_LLM_ID
        active_llm_id = None
        if active_provider == "openai" and openai_llm:
            active_llm_id = openai_llm.id
        elif active_provider == "ollama" and ollama_llm:
            active_llm_id = ollama_llm.id
        elif openai_llm: # Fallback
            active_llm_id = openai_llm.id
            
        if active_llm_id:
            db.merge(SystemSetting(key="AGENT_LLM_ID", value=str(active_llm_id), description="Active LLM Agent Model ID"))
            print(f"Set AGENT_LLM_ID to {active_llm_id}")

        # EMBEDDING_MODEL_ID
        if emb_model:
            db.merge(SystemSetting(key="EMBEDDING_MODEL_ID", value=str(emb_model.id), description="Active Embedding Model ID"))
            print(f"Set EMBEDDING_MODEL_ID to {emb_model.id}")

        # RERANKER_MODEL_ID
        if rerank_model:
            db.merge(SystemSetting(key="RERANKER_MODEL_ID", value=str(rerank_model.id), description="Active Reranker Model ID"))
            print(f"Set RERANKER_MODEL_ID to {rerank_model.id}")

        # LLM_TIMEOUT
        db.merge(SystemSetting(key="LLM_TIMEOUT", value=str(llm_timeout), description="LLM Request Timeout (seconds)"))
        print(f"Set LLM_TIMEOUT to {llm_timeout}")

        db.commit()
        print("Migration completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
