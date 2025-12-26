from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyHttpUrl, field_validator

class Settings(BaseSettings):
    """
    应用配置类
    加载环境变量
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Project Info
    PROJECT_NAME: str = "SeerLord AI"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=[], description="List of origins allowed for CORS"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # LLM Configuration
    LLM_PROVIDER: str = Field("openai", description="Provider: 'openai' or 'ollama'")
    LLM_TIMEOUT: int = Field(30, description="LLM Request Timeout in seconds")
    LLM_MAX_RETRIES: int = Field(3, description="Maximum number of retries for LLM calls")
    
    # OpenAI Config
    OPENAI_API_KEY: str | None = Field(None, description="OpenAI API Key (Required if provider is openai)")
    OPENAI_MODEL: str = Field("gpt-4o", description="OpenAI Model Name")
    OPENAI_API_BASE: str = Field("https://api.openai.com/v1", description="OpenAI API Base URL")

    # Ollama Config
    OLLAMA_BASE_URL: str = Field("http://localhost:11434", description="Ollama Base URL")
    OLLAMA_MODEL: str = Field("qwen3:8b", description="Ollama Model Name")

    # Embedding Config
    EMBEDDING_PROVIDER: str = Field("openai", description="Provider for embeddings: 'openai' or 'ollama'")
    EMBEDDING_MODEL: str = Field("text-embedding-3-small", validation_alias="EMBEDDINGS_MODEL", description="Embedding model name")
    EMBEDDING_DIM: int = Field(1536, description="Dimension of the embedding vector (1536 for openai-small, 768 for nomic-embed-text)")
    EMBEDDINGS_API_KEY: str | None = Field(None, description="API Key for embeddings if different from OpenAI")
    EMBEDDINGS_ENDPOINT: str | None = Field(None, description="Base URL for embeddings if different from OpenAI")
    EMBEDDINGS_TIMEOUT_SEC: int = Field(600, description="Embedding request timeout in seconds")
    EMBEDDINGS_BATCH_SIZE: int = Field(128, description="Batch size for embedding requests")
    
    # Reranker Configuration
    RERANKER_ENDPOINT: str | None = Field(None, description="Reranker API Endpoint")
    RERANKER_MODEL: str | None = Field(None, description="Reranker Model Name")

    # Qdrant Configuration
    QDRANT_URL: str | None = Field(None, description="Qdrant URL (e.g. http://localhost:6333)")
    QDRANT_API_KEY: str | None = Field(None, description="Qdrant API Key")
    QDRANT_COLLECTION: str = Field("agent_memory", description="Qdrant Collection Name")
    MEMORY_COLLECTION: str = Field("seerlord_long_term_memory", description="Dedicated Qdrant Collection for Long Term Memory")
    SIM_METRIC: str = Field("Cosine", description="Similarity Metric (Cosine, Euclidean, Dot)")

    # Database Configuration
    DB_HOST: str | None = None
    DB_PORT: int = 5432
    DB_USERNAME: str | None = None
    DB_PASSWORD: str | None = None
    DB_DATABASE: str | None = None
    
    # Computed Database URL (Internal use)
    _DATABASE_URL: str | None = None

    @property
    def DATABASE_URL(self) -> str | None:
        """
        优先使用显式配置的 DATABASE_URL。
        如果没有，则尝试根据 DB_* 字段构建。
        """
        if self._DATABASE_URL:
            return self._DATABASE_URL
            
        if self.DB_HOST and self.DB_USERNAME and self.DB_DATABASE:
            return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"
        
        return None

    @field_validator("OPENAI_API_KEY")
    def validate_api_key(cls, v, values):
        # 注意：Pydantic v2 validation logic might be different, using values.data
        # 但这里我们在运行时动态检查更灵活
        return v
    
    # 插件目录
    PLUGIN_DIR: str = Field("server/plugins", description="Directory containing plugins")

    # LangSmith / LangChain Tracing
    LANGCHAIN_TRACING_V2: bool = Field(False, description="Enable LangChain Tracing")
    LANGCHAIN_API_KEY: str | None = Field(None, description="LangChain API Key")
    LANGCHAIN_PROJECT: str = Field("default", description="LangChain Project Name")

    # Auth
    SECRET_KEY: str = Field("09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7", description="JWT Secret Key")
    ALGORITHM: str = "HS256"
    # 登录会话过期时间：24小时 (1440分钟)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALLOW_DEFAULT_TENANT_FALLBACK: bool = Field(False, description="Allow fallback to default admin tenant when API Key is missing")

    # 首启初始化（仅当用户表为空时可用）
    SETUP_TOKEN: str | None = Field(None, description="First-boot setup token. If not set, setup API is disabled.")

settings = Settings()
