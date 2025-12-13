from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel
from server.core.config import settings
from server.core.llm import get_llm

class TestSchema(BaseModel):
    summary: str

try:
    print(f"OLLAMA_BASE_URL: {settings.OLLAMA_BASE_URL}")
    print(f"LLM_PROVIDER: {settings.LLM_PROVIDER}")
    
    print("Initializing LLM via get_llm...")
    llm = get_llm(temperature=0)
    print(f"LLM Class: {type(llm)}")
    
    messages = [
        SystemMessage(content="You are a helper."),
        HumanMessage(content="Hello")
    ]
    
    print(f"Testing invoke with messages: {messages}")
    response = llm.invoke(messages)
    print(f"Invoke response: {response}")

    print("Testing structured output...")
    structured_llm = llm.with_structured_output(TestSchema)
    result = structured_llm.invoke(messages)
    print(f"Structured result: {result}")

except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()
