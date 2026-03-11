"""
Orchestrator - serial multi-agent coordination
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio

from .agent import Agent, AgentMessage
from .base import AgentConfig, ExecutionOutput
from .task_tracker import TaskTracker
from .ai_client import AIClient


class Orchestrator:
    """Serial multi-agent orchestrator"""

    def __init__(
        self,
        workflow_config: Dict[str, Any],
        tracker: Optional[TaskTracker] = None,
        ai_client: Optional[AIClient] = None,
        router: Optional[Any] = None
    ):
        self.workflow = workflow_config
        self.tracker = tracker or TaskTracker()
        self.ai_client = ai_client or AIClient.get_instance()
        self.router = router

        agents_cfg = workflow_config.get("agents", {})

        planner_cfg = agents_cfg.get("planner", {})
        reviewer_cfg = agents_cfg.get("reviewer", {})
        workers_cfg = agents_cfg.get("workers", [])

        self.planner = Agent(
            config=AgentConfig(
                name=planner_cfg.get("name", "planner"),
                role=planner_cfg.get("role", "planner"),
                system_prompt=planner_cfg.get("system_prompt", "你是任务规划专家。"),
                execution_profile=planner_cfg.get("execution_profile", "planner"),
                ai_client=self.ai_client
            )
        )

        self.workers: List[Agent] = []
        for i, wc in enumerate(workers_cfg, 1):
            self.workers.append(
                Agent(
                    config=AgentConfig(
                        name=wc.get("name", f"worker_{i}"),
                        role=wc.get("role", "worker"),
                        system_prompt=wc.get("system_prompt", "你是任务执行专家。"),
                        execution_profile=wc.get("execution_profile", "worker"),
                        skills=wc.get("skills", []),
                        ai_client=self.ai_client
                    )
                )
            )

        self.reviewer = Agent(
            config=AgentConfig(
                name=reviewer_cfg.get("name", "reviewer"),
                role=reviewer_cfg.get("role", "reviewer"),
                system_prompt=reviewer_cfg.get("system_prompt", "你是质量审查与总结专家。"),
                execution_profile=reviewer_cfg.get("execution_profile", "reviewer"),
                ai_client=self.ai_client
            )
        )

    def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        track: bool = True,
        parallel_workers: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """Run the multi-agent flow"""
        if parallel_workers:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(self.run_async(task, context=context, track=track))
            raise RuntimeError("Async loop detected. Use run_async() for parallel workers.")

        params = {"task": task, "context": context or {}}
        task_id = self.tracker.create_task(self.workflow.get("name", "agent_flow"), params) if track else ""

        base_context = context or {}

        planner_msg = AgentMessage(
            task_id=task_id,
            sender="user",
            receiver=self.planner.name,
            role="planner",
            content=task,
            context=base_context,
            metadata={"timestamp": datetime.now().isoformat()}
        )

        if track:
            self.tracker.update_step(task_id, self.planner.name, "running")
        plan_resp = self.planner.run(planner_msg)
        if track:
            self.tracker.update_step(task_id, self.planner.name, "completed", output=plan_resp.content)

        worker_outputs = []
        for worker in self.workers:
            worker_msg = AgentMessage(
                task_id=task_id,
                sender=self.planner.name,
                receiver=worker.name,
                role="worker",
                content=f"任务：{task}\n\n规划：\n{plan_resp.content}",
                context=base_context,
                metadata={"timestamp": datetime.now().isoformat()}
            )
            if track:
                self.tracker.update_step(task_id, worker.name, "running")
            worker_resp = worker.run(worker_msg, router=self.router)
            worker_outputs.append({"agent": worker.name, "output": worker_resp.content})
            if track:
                self.tracker.update_step(task_id, worker.name, "completed", output=worker_resp.content)

        reviewer_msg = AgentMessage(
            task_id=task_id,
            sender="orchestrator",
            receiver=self.reviewer.name,
            role="reviewer",
            content=(
                f"任务：{task}\n\n规划：\n{plan_resp.content}\n\n"
                f"Worker 输出：\n{worker_outputs}"
            ),
            context=base_context,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        if track:
            self.tracker.update_step(task_id, self.reviewer.name, "running")
        reviewer_resp = self.reviewer.run(reviewer_msg)
        if track:
            self.tracker.update_step(task_id, self.reviewer.name, "completed", output=reviewer_resp.content)
            self.tracker.complete_task(task_id, {
                "plan": plan_resp.content,
                "workers": worker_outputs,
                "final": reviewer_resp.content
            })

        return task_id, {
            "plan": plan_resp.content,
            "workers": worker_outputs,
            "final": reviewer_resp.content
        }

    async def run_async(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        track: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """Run the multi-agent flow with parallel workers"""
        params = {"task": task, "context": context or {}}
        task_id = self.tracker.create_task(self.workflow.get("name", "agent_flow"), params) if track else ""

        base_context = context or {}

        planner_msg = AgentMessage(
            task_id=task_id,
            sender="user",
            receiver=self.planner.name,
            role="planner",
            content=task,
            context=base_context,
            metadata={"timestamp": datetime.now().isoformat()}
        )

        if track:
            self.tracker.update_step(task_id, self.planner.name, "running")
        plan_resp = self.planner.run(planner_msg)
        if track:
            self.tracker.update_step(task_id, self.planner.name, "completed", output=plan_resp.content)

        async def run_worker(worker: Agent) -> Dict[str, Any]:
            worker_msg = AgentMessage(
                task_id=task_id,
                sender=self.planner.name,
                receiver=worker.name,
                role="worker",
                content=f"任务：{task}\n\n规划：\n{plan_resp.content}",
                context=base_context,
                metadata={"timestamp": datetime.now().isoformat()}
            )
            if track:
                self.tracker.update_step(task_id, worker.name, "running")
            worker_resp = await asyncio.to_thread(worker.run, worker_msg, self.router)
            if track:
                self.tracker.update_step(task_id, worker.name, "completed", output=worker_resp.content)
            return {"agent": worker.name, "output": worker_resp.content}

        worker_outputs = []
        if self.workers:
            worker_outputs = await asyncio.gather(*[run_worker(worker) for worker in self.workers])

        reviewer_msg = AgentMessage(
            task_id=task_id,
            sender="orchestrator",
            receiver=self.reviewer.name,
            role="reviewer",
            content=(
                f"任务：{task}\n\n规划：\n{plan_resp.content}\n\n"
                f"Worker 输出：\n{worker_outputs}"
            ),
            context=base_context,
            metadata={"timestamp": datetime.now().isoformat()}
        )
        if track:
            self.tracker.update_step(task_id, self.reviewer.name, "running")
        reviewer_resp = self.reviewer.run(reviewer_msg)
        if track:
            self.tracker.update_step(task_id, self.reviewer.name, "completed", output=reviewer_resp.content)
            self.tracker.complete_task(task_id, {
                "plan": plan_resp.content,
                "workers": worker_outputs,
                "final": reviewer_resp.content
            })

        return task_id, {
            "plan": plan_resp.content,
            "workers": worker_outputs,
            "final": reviewer_resp.content
        }
