from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator

class UIDesignerState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    ui_design_spec: Optional[str]        # Step 1: JSONC Output
    implementation_prompt: Optional[str] # Step 1: MD Output
    final_code: Optional[str]            # Step 2: Vue Code
    tenant_id: Optional[str]
    user_id: Optional[str]
    user_description: Optional[str]      # Optional user input to narrow down LLM judgment
    skills_context: Optional[str]
    used_skill_ids: Optional[List[str]]
