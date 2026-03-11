"""
Agent abstractions and message protocol
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

from .ai_client import AIClient
from .base import AgentConfig, SkillInput, ExecutionInput, ExecutionOutput

if TYPE_CHECKING:
    from .router import Router


@dataclass
class AgentMessage(ExecutionInput):
    """Agent-to-Agent message protocol"""
    pass


class Agent:
    """LLM-backed agent"""

    def __init__(self, config: AgentConfig):
        self.name = config.name
        self.role = config.role
        self.system_prompt = config.system_prompt
        self.execution_profile = config.execution_profile
        self.skills = config.skills
        self.ai_client = config.ai_client or AIClient.get_instance()

    def run(self, message: AgentMessage, router: Optional["Router"] = None) -> ExecutionOutput:
        """Run the agent and return a response"""
        if router:
            skill_name = self._resolve_skill(message, router)
            if skill_name:
                return self._call_skill(message, router, skill_name)
        return self._call_llm(message)

    def _call_llm(self, message: AgentMessage) -> ExecutionOutput:
        messages = self._build_messages(message)
        response = self.ai_client.call_ai(messages=messages, execution_profile=self.execution_profile)

        content = self.ai_client.extract_content(response)
        usage = response.get("usage", {})

        return ExecutionOutput(
            task_id=message.task_id,
            sender=self.name,
            receiver=message.sender,
            role=self.role,
            content=content,
            success=True,
            data={"content": content},
            next_context=message.context,
            metadata={
                "model": response.get("model"),
                "tokens_used": usage.get("total_tokens", 0),
                "timestamp": datetime.now().isoformat()
            }
        )

    def _resolve_skill(self, message: AgentMessage, router: "Router") -> Optional[str]:
        if not self.skills:
            return None

        explicit = message.context.get("use_skills", []) if message.context else []
        for skill in explicit:
            if skill in self.skills:
                return skill

        content = message.content.lower()
        for skill_name in self.skills:
            keywords = router.get_skill_keywords(skill_name)
            for keyword in keywords:
                if keyword.lower() in content:
                    return skill_name
        return None

    def _call_skill(self, message: AgentMessage, router: "Router", skill_name: str) -> ExecutionOutput:
        skill_input = SkillInput(
            task_id=message.task_id,
            sender=self.name,
            receiver=skill_name,
            role="skill",
            content=message.content,
            params={"task": message.content},
            context=message.context,
            attachments=message.attachments,
            metadata=message.metadata,
            execution_profile=self.execution_profile
        )

        skill_output = router.run_skill(skill_name, skill_input)

        return ExecutionOutput(
            task_id=message.task_id,
            sender=self.name,
            receiver=message.sender,
            role=self.role,
            content=str(skill_output.data) if skill_output.success else str(skill_output.error),
            success=skill_output.success,
            data=skill_output.data,
            error=skill_output.error,
            error_type=skill_output.error_type,
            next_context=skill_output.next_context,
            metadata={
                "skill_used": skill_name,
                "timestamp": datetime.now().isoformat()
            }
        )

    def _build_messages(self, message: AgentMessage) -> List[Dict[str, str]]:
        user_content = self._build_user_content(message)
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content}
        ]

    def _build_user_content(self, message: AgentMessage) -> str:
        context_text = ""
        if message.context:
            context_text = "\n\n上下文：\n" + "\n".join(
                [f"- {k}: {v}" for k, v in message.context.items()]
            )

        attachment_text = ""
        if message.attachments:
            attachment_text = "\n\n附件：\n" + "\n".join([str(a) for a in message.attachments])

        return (
            f"任务内容：\n{message.content}"
            f"{context_text}"
            f"{attachment_text}\n"
        )
