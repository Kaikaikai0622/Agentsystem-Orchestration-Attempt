#!/usr/bin/env python3
"""
Test each agent with the same question and print full outputs.
"""

import sys
import os
from datetime import datetime

from dotenv import load_dotenv
import yaml

from agent import Agent, AgentMessage
from agent.base import AgentConfig
from agent.ai_client import AIClient


QUESTION = "你是谁？什么模型版本？可以干什么？"


def build_agents(workflow_path: str = "WORKFLOWS/agent_flow.yaml"):
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    agents_cfg = workflow.get("agents", {})
    planner_cfg = agents_cfg.get("planner", {})
    reviewer_cfg = agents_cfg.get("reviewer", {})
    workers_cfg = agents_cfg.get("workers", [])

    ai_client = AIClient.get_instance()

    planner = Agent(
        config=AgentConfig(
            name=planner_cfg.get("name", "planner"),
            role=planner_cfg.get("role", "planner"),
            system_prompt=planner_cfg.get("system_prompt", "你是任务规划专家。"),
            execution_profile=planner_cfg.get("execution_profile", "planner"),
            ai_client=ai_client,
        )
    )

    workers = []
    for i, wc in enumerate(workers_cfg, 1):
        workers.append(
            Agent(
                config=AgentConfig(
                    name=wc.get("name", f"worker_{i}"),
                    role=wc.get("role", "worker"),
                    system_prompt=wc.get("system_prompt", "你是任务执行专家。"),
                    execution_profile=wc.get("execution_profile", "worker"),
                    skills=wc.get("skills", []),
                    ai_client=ai_client,
                )
            )
        )

    reviewer = Agent(
        config=AgentConfig(
            name=reviewer_cfg.get("name", "reviewer"),
            role=reviewer_cfg.get("role", "reviewer"),
            system_prompt=reviewer_cfg.get("system_prompt", "你是质量审查与总结专家。"),
            execution_profile=reviewer_cfg.get("execution_profile", "reviewer"),
            ai_client=ai_client,
        )
    )

    return planner, workers, reviewer


def main() -> int:
    load_dotenv()

    planner, workers, reviewer = build_agents()

    print("=" * 60)
    print("Three-Agent Identity Test")
    print("=" * 60)
    print(f"Question: {QUESTION}")
    print()

    def run_agent(agent):
        msg = AgentMessage(
            task_id="",
            sender="user",
            receiver=agent.name,
            role=agent.role,
            content=QUESTION,
            context={},
            metadata={"timestamp": datetime.now().isoformat()},
        )
        return agent.run(msg)

    print("=== Planner Output ===")
    planner_out = run_agent(planner)
    print(planner_out.content)
    print()

    for idx, worker in enumerate(workers, 1):
        print(f"=== Worker {idx} ({worker.name}) Output ===")
        worker_out = run_agent(worker)
        print(worker_out.content)
        print()

    print("=== Reviewer Output ===")
    reviewer_out = run_agent(reviewer)
    print(reviewer_out.content)
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
