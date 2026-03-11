"""
Test script for multi-agent flow
验证多 Agent 系统的协作效果
"""

import sys
import os
from dotenv import load_dotenv

# 设置 UTF-8 编码（Windows GBK 问题修复）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load environment variables
load_dotenv()

from agent import Orchestrator

def test_agent_flow():
    """测试多 Agent 流程"""

    print("=" * 60)
    print("Multi-Agent Flow Test")
    print("=" * 60)

    # 加载 agent_flow 配置
    import yaml
    workflow_path = "WORKFLOWS/agent_flow.yaml"

    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = yaml.safe_load(f)

    print(f"\nWorkflow: {workflow.get('name')}")
    print(f"Description: {workflow.get('description')}")

    # 显示配置的 Agent
    agents_cfg = workflow.get("agents", {})
    print("\n=== Configured Agents ===")
    print(f"\n1. Planner Agent:")
    print(f"   - Name: {agents_cfg.get('planner', {}).get('name', 'N/A')}")
    print(f"   - Role: {agents_cfg.get('planner', {}).get('role', 'N/A')}")
    print(f"   - Execution Profile: {agents_cfg.get('planner', {}).get('execution_profile', 'N/A')}")

    print(f"\n2. Worker Agents:")
    for i, worker in enumerate(agents_cfg.get("workers", []), 1):
        print(f"   Worker {i}:")
        print(f"     - Name: {worker.get('name', 'N/A')}")
        print(f"     - Role: {worker.get('role', 'N/A')}")
        print(f"     - Execution Profile: {worker.get('execution_profile', 'N/A')}")
        skills = worker.get('skills', [])
        if skills:
            print(f"     - Skills: {', '.join(skills)}")
        system_prompt = worker.get('system_prompt', '')
        if system_prompt:
            preview = system_prompt[:100] + '...' if len(system_prompt) > 100 else system_prompt
            print(f"     - System Prompt Preview: {preview}")

    print(f"\n3. Reviewer Agent:")
    print(f"   - Name: {agents_cfg.get('reviewer', {}).get('name', 'N/A')}")
    print(f"   - Role: {agents_cfg.get('reviewer', {}).get('role', 'N/A')}")
    print(f"   - Execution Profile: {agents_cfg.get('reviewer', {}).get('execution_profile', 'N/A')}")

    print("\n" + "=" * 60)
    print("Starting Multi-Agent Execution...")
    print("=" * 60)

    # 创建 Orchestrator
    try:
        orchestrator = Orchestrator(workflow)
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize Orchestrator: {e}")
        return False

    # 定义测试任务
    test_task = os.getenv(
        "TEST_TASK",
        "帮我计算：如果昨天苹果的价格是每斤 5 元，今天涨了 20%，我买了 3 斤，总共花了多少钱？"
    )

    print(f"\n用户任务：\n{test_task}\n")

    # 运行多 Agent 流程
    try:
        task_id, result = orchestrator.run(test_task, track=True)
    except Exception as e:
        print(f"\n[ERROR] Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 显示结果
    print("\n" + "=" * 60)
    print("Execution Results")
    print("=" * 60)

    print(f"\n[OK] Task ID: {task_id}")

    print(f"\n=== 1. Planner Output ===")
    plan = result.get("plan", "")
    print(plan)

    print(f"\n=== 2. Worker Outputs ===")
    workers = result.get("workers", [])
    for i, worker_result in enumerate(workers, 1):
        agent_name = worker_result.get("agent", f"worker_{i}")
        output = worker_result.get("output", "")
        print(f"\n[{agent_name}]")
        print(output)

    print(f"\n=== 3. Reviewer Output ===")
    final = result.get("final", "")
    print(final)

    print("\n" + "=" * 60)
    print("[OK] Multi-Agent Test Completed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = test_agent_flow()
    sys.exit(0 if success else 1)
