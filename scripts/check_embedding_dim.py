import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from loguru import logger
from server.ske.llm_setup import initialize_ske_llm
from llama_index.core import Settings

async def main():
    initialize_ske_llm()
    text = "Hello SeerLord"
    embedding = await Settings.embed_model.aget_text_embedding(text)
    logger.info(f"Embedding dimension: {len(embedding)}")

if __name__ == "__main__":
    asyncio.run(main())
