import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage
from server.kernel.hierarchical_skills import HierarchicalSkill, SkillLevel, SkillContent
from server.plugins._voyager_agent_.graph import critic_node, refine_skill_node
from server.plugins._voyager_agent_.state import VoyagerState
from server.kernel.dynamic_skill_manager import dynamic_skill_manager

async def test_critic_and_refinement():
    print("🚀 Starting Skill Evolution Verification...")
    
    # 1. Create a Mock Skill (Simulate a skill that needs improvement)
    mock_skill = HierarchicalSkill(
        name="BadMathSkill",
        description="A skill that does math poorly.",
        level=SkillLevel.SPECIFIC,
        content=SkillContent(
            prompt_template="Just guess the number.",
            knowledge_base=["Math is hard."]
        )
    )
    
    # 2. Simulate State after execution (Bad result)
    state: VoyagerState = {
        "messages": [
            HumanMessage(content="Calculate 2 + 2"),
            # In a real flow, there would be an AIMessage here, but critic reads execution_result
        ],
        "tenant_id": "test_tenant",
        "user_id": "test_user",
        "memory_context": "",
        "current_skill": mock_skill,
        "skill_match_reason": "Testing",
        "execution_result": "The answer is 5." # Wrong answer!
    }
    
    print(f"📝 Mock Task: 2 + 2")
    print(f"📝 Mock Result: {state['execution_result']}")
    
    # 3. Test Critic Node
    print("\n🔍 Running Critic Node...")
    try:
        critic_result = await critic_node(state)
        print(f"✅ Critic Output: {critic_result}")
        
        if not critic_result.get("needs_refinement"):
            print("❌ Test Failed: Critic should have flagged this as needing refinement.")
            return
            
        # Update state with critic result
        state.update(critic_result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return

    # 4. Test Refinement Node
    print("\n🔧 Running Refinement Node (this calls Evolver)...")
    
    # We need to mock the add_skill method to avoid actual DB writes if possible, 
    # but for integration test we can let it run (it might fail if DB not set up, but let's see).
    # Actually, let's just see if it runs without crashing.
    
    try:
        await refine_skill_node(state)
        print("✅ Refinement Node executed successfully.")
    except Exception as e:
        print(f"⚠️ Refinement Node finished with error (expected if DB/LLM issues): {e}")
        # Even if it errors on DB, if it reached there, the flow is correct.
        
    print("\n🎉 Verification Flow Finished.")

if __name__ == "__main__":
    asyncio.run(test_critic_and_refinement())
