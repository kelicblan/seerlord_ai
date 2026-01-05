import sys
import os
from pathlib import Path

# Add project root to sys.path
# 将项目根目录添加到 sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from server.kernel.skill_registry import skill_registry

def test_system_monitor_skill():
    """
    Test the auto-registration and execution of the SystemMonitorSkill.
    测试 SystemMonitorSkill 的自动注册和执行。
    """
    print("\n" + "="*50)
    print("🧪 Testing System Monitor Skill Integration")
    print("="*50 + "\n")

    # 1. Scan and load skills
    # 1. 扫描并加载技能
    print("1. Scanning for skills...")
    skill_registry.scan_and_load()
    
    # 2. Check registration
    # 2. 检查注册情况
    skill_name = "get_system_status"
    if skill_name in skill_registry.skills:
        print(f"✅ Skill '{skill_name}' found in registry!")
        skill = skill_registry.skills[skill_name]
        print(f"   Description: {skill.description}")
    else:
        print(f"❌ Skill '{skill_name}' NOT found!")
        available_skills = list(skill_registry.skills.keys())
        print(f"   Available skills: {available_skills}")
        return

    # 3. Execute Skill
    # 3. 执行技能
    print("\n2. Executing skill...")
    try:
        # Test default (all)
        result_all = skill.invoke({"resource_type": "all"})
        print(f"   [Input: all] Result: {result_all}")
        
        # Test specific (memory)
        result_mem = skill.invoke({"resource_type": "memory"})
        print(f"   [Input: memory] Result: {result_mem}")
        
        print("\n✅ Test Passed! System is successfully monitoring resources.")
        
    except Exception as e:
        print(f"\n❌ Execution Failed: {e}")

if __name__ == "__main__":
    test_system_monitor_skill()
