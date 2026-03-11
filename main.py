#!/usr/bin/env python3
"""
Agent System - 主入口
市场情报分析 Agent 系统
"""

import os
import sys
import logging

from dotenv import load_dotenv
from agent import Router, TaskTracker

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()

    # 检查 API Key 是否配置
    required_env_groups = [
        ['MOONSHOT_API_KEY', 'ANTHROPIC_API_KEY'],
        ['ANTHROPIC_REVIEWER_API_KEY']
    ]
    missing_groups = [group for group in required_env_groups if not any(os.getenv(var) for var in group)]

    if missing_groups:
        logger.error("❌ 缺少必需的环境变量:")
        for group in missing_groups:
            logger.error(f"   - {' / '.join(group)}")
        logger.error("\n请在 .env 文件中配置 API Keys")
        logger.error("可以复制 .env.example 为 .env 并填入实际的值")
        sys.exit(1)

    # 初始化 Router
    router = Router()

    logger.info("""
╔════════════════════════════════════════════════════════╗
║         Agent System - 市场情报分析系统                   ║
╚════════════════════════════════════════════════════════╝
    """)

    # 显示可用的工作流
    logger.info("📋 可用的工作流:")
    workflows = router.list_workflows()
    for i, wf in enumerate(workflows, 1):
        logger.info(f"  {i}. {wf['name']} - {wf['description']} ({wf['steps']} 步)")

    logger.info("\n🛠️  可用的技能:")
    skills = router.list_skills()
    for i, skill in enumerate(skills, 1):
        desc = skill['description'][:40] + "..." if len(skill['description']) > 40 else skill['description']
        logger.info(f"  {i}. {skill['name']} - {desc}")

    logger.info("\n⚙️  可用的执行配置 (Execution Profiles):")
    profiles = router.list_execution_profiles()
    for i, profile in enumerate(profiles, 1):
        purpose = profile.get("purpose", "")
        desc = profile.get("description", "")
        provider = profile.get("provider", "")
        model = profile.get("model", "")
        label = f"{profile['name']} - {purpose}" if purpose else profile["name"]
        logger.info(f"  {i}. {label} ({provider}/{model})")
        if desc and desc != purpose:
            logger.info(f"     {desc}")

    logger.info("\n💡 提示: skill 工作流用 router.execute_workflow()，agent_flow 用 router.execute_agent_flow()")

    # 使用示例
    logger.info("\n📖 使用示例:")
    logger.info("  # 执行 skill 工作流")
    logger.info("  router.execute_workflow('workflow_name', params={'task': '你的任务'})")
    logger.info("  # 或")
    logger.info("  router.execute_agent_flow('agent_flow', params={'task': '你的任务'})")


if __name__ == "__main__":
    main()
