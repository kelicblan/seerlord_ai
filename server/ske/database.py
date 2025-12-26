from neo4j import AsyncGraphDatabase, AsyncDriver
from loguru import logger
from server.ske.config import ske_settings

class Neo4jManager:
    """
    Manages the Neo4j database connection and initialization.
    """
    _driver: AsyncDriver = None

    @classmethod
    async def get_driver(cls) -> AsyncDriver:
        """
        Returns the active Neo4j driver, creating it if necessary.
        """
        if cls._driver is None:
            try:
                logger.info(f"Connecting to Neo4j at {ske_settings.NEO4J_URI}...")
                cls._driver = AsyncGraphDatabase.driver(
                    ske_settings.NEO4J_URI,
                    auth=(ske_settings.NEO4J_USERNAME, ske_settings.NEO4J_PASSWORD)
                )
                # Verify connection
                await cls._driver.verify_connectivity()
                logger.info("Successfully connected to Neo4j.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise e
        return cls._driver

    @classmethod
    async def close(cls):
        """
        Closes the Neo4j driver connection.
        """
        if cls._driver:
            await cls._driver.close()
            cls._driver = None
            logger.info("Neo4j connection closed.")

    @classmethod
    async def create_indexes(cls):
        """
        Creates necessary indexes and constraints in Neo4j.
        Includes Vector Index for Entity embeddings.
        """
        driver = await cls.get_driver()
        async with driver.session(database=ske_settings.NEO4J_DATABASE) as session:
            logger.info("Creating Neo4j indexes...")
            
            # 1. Entity ID Unique Constraint (also acts as an index)
            await session.run(
                "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE"
            )
            
            # 2. Entity Name Index (for fast lookups)
            await session.run(
                "CREATE INDEX entity_name_index IF NOT EXISTS FOR (n:Entity) ON (n.name)"
            )

            # 3. Vector Index for Entity Embeddings
            # Using Neo4j 5.x+ Vector Index syntax
            # Note: Backticks around keys in OPTIONS are important for some versions, but standard JSON keys usually work.
            # We use `vector.dimensions` and `vector.similarity_function`.
            
            vector_index_query = f"""
            CREATE VECTOR INDEX entity_embedding_index IF NOT EXISTS
            FOR (n:Entity) ON (n.embedding)
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {ske_settings.SKE_EMBEDDING_DIM},
                `vector.similarity_function`: 'cosine'
            }}}}
            """
            
            try:
                await session.run(vector_index_query)
                logger.info(f"Vector index 'entity_embedding_index' created/verified (dim={ske_settings.SKE_EMBEDDING_DIM}, metric=cosine).")
            except Exception as e:
                logger.error(f"Failed to create entity vector index: {e}")
                raise e

            # 4. Vector Index for Chunk Embeddings (Added for Task 3)
            chunk_vector_index_query = f"""
            CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS {{indexConfig: {{
                `vector.dimensions`: {ske_settings.SKE_EMBEDDING_DIM},
                `vector.similarity_function`: 'cosine'
            }}}}
            """
            
            try:
                await session.run(chunk_vector_index_query)
                logger.info(f"Vector index 'chunk_embedding_index' created/verified (dim={ske_settings.SKE_EMBEDDING_DIM}, metric=cosine).")
            except Exception as e:
                logger.error(f"Failed to create chunk vector index: {e}")
                # We don't raise here if it fails, just log it, as it might be an optional enhancement
                # But for consistency, let's treat it as critical for Task 3
                raise e

async def get_driver() -> AsyncDriver:
    """
    Helper function to get the Neo4j driver instance.
    """
    return await Neo4jManager.get_driver()
