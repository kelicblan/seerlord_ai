from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class SKESettings(BaseSettings):
    """
    SEERLORD Knowledge Engine Configuration
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # Neo4j Configuration
    NEO4J_URL: str = Field(..., description="Neo4j Connection URL (e.g. bolt://localhost:7687)")
    NEO4J_USERNAME: str = Field("neo4j", description="Neo4j Username")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j Password")
    NEO4J_DATABASE: str = Field("neo4j", description="Neo4j Database Name")

    # Embedding Configuration
    # Use global EMBEDDING_DIM from .env (defaults to 1024 for text-embedding-v4)
    SKE_EMBEDDING_DIM: int = Field(1024, validation_alias="EMBEDDING_DIM", description="Dimension of the embedding vector for Knowledge Graph")

    @property
    def NEO4J_URI(self) -> str:
        """
        Corrects the URI scheme if necessary.
        The python neo4j driver expects bolt:// or neo4j://.
        If the env var is http://, we replace it.
        """
        uri = self.NEO4J_URL
        if uri.startswith("http://"):
            return uri.replace("http://", "bolt://")
        if uri.startswith("https://"):
            return uri.replace("https://", "bolt+s://") # Assuming secure if https
        return uri

ske_settings = SKESettings()
