from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional
from server.rag.manager import RAGManager
import asyncio

class RetrievalInput(BaseModel):
    query: str = Field(description="The query string to search for in the knowledge base.")
    kb_id: str = Field(description="The ID of the knowledge base to search.", default=None)

class RetrievalTool(BaseTool):
    name: str = "knowledge_retrieval"
    description: str = "Search for information in the knowledge base. Use this when you need historical data, technical docs, or past cases."
    args_schema: Type[BaseModel] = RetrievalInput
    
    # Exclude from Pydantic fields to avoid validation error, 
    # but BaseTool allows private attrs.
    _rag_manager: RAGManager = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rag_manager = RAGManager()

    def _run(self, query: str, kb_id: str = None) -> str:
        """Synchronous wrapper for async search"""
        # This is a fallback if called synchronously
        return "Please use the async version of this tool."

    async def _arun(self, query: str, kb_id: str = None) -> str:
        """Use the tool asynchronously."""
        try:
            # If kb_id is not provided, we might want to search all or a default one.
            # For now, let's assume the agent passes it or we search without filter (if supported).
            results = await self._rag_manager.search(query, kb_id=kb_id, top_k=5)
            if not results:
                return "No relevant information found in the knowledge base."
            
            # Format results
            formatted_list = []
            for res in results:
                source = res['metadata'].get('filename', 'Unknown')
                formatted_list.append(f"Source: {source}\nContent: {res['text']}")
            
            return "\n---\n".join(formatted_list)
        except Exception as e:
            return f"Error retrieving information: {e}"
