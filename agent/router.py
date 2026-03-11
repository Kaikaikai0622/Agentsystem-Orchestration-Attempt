"""
Router - 工作流解析和技能调度器
负责解析 YAML 工作流定义并按顺序调用技能
"""

import yaml
import time
import re
import logging
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from functools import wraps

from .base import SkillInput, SkillOutput, BaseSkill
from .task_tracker import TaskTracker, TaskStatus
from .ai_client import AIClient
from .orchestrator import Orchestrator
from .skill_registry import get_skill_definition
from .errors import AgentError, ValidationError, ProviderError, RetryableError


logger = logging.getLogger(__name__)

DEFAULT_SKILL_KEYWORDS = {
    "data_analyst": ["sql", "select", "join", "pandas", "dataframe", "统计", "分析", "订单", "数据"],
    "web_search": ["搜索", "查找", "网页", "google", "bing"],
    "ai_qa": []
}


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: Preserve and return the last failure details instead of generic "Max retries exceeded".
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    if result.success:
                        return result
                    if result.error_type == "validation":
                        return result
                    logger.warning("Skill failed without exception; retrying", extra={"attempt": attempt + 1})
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                except AgentError as e:
                    if not e.retryable:
                        return SkillOutput(success=False, error=str(e), error_type=e.error_type)
                    if attempt == max_retries - 1:
                        return SkillOutput(success=False, error=str(e), error_type=e.error_type)
                    logger.exception("Skill raised retryable error; retrying", extra={"attempt": attempt + 1})
                    time.sleep(delay * (attempt + 1))
                except Exception as e:
                    if attempt == max_retries - 1:
                        return SkillOutput(success=False, error=str(e), error_type="error")
                    logger.exception("Skill raised exception; retrying", extra={"attempt": attempt + 1})
                    time.sleep(delay * (attempt + 1))
            return SkillOutput(success=False, error="Max retries exceeded")
        return wrapper
    return decorator


class Router:
    """工作流路由器"""

    def __init__(self, skills_dir: str = "SKILLS", workflows_dir: str = "WORKFLOWS"):
        self.skills_dir = Path(skills_dir)
        self.workflows_dir = Path(workflows_dir)
        self.tracker = TaskTracker()
        self.ai_client = AIClient.get_instance()
        self.skills: Dict[str, Any] = {}  # 已加载的技能
        self.skill_metadata: Dict[str, Dict[str, Any]] = {}

    def _import_skill_module(self, skill_dir: Path, skill_name: str) -> None:
        module_path = f"SKILLS.{skill_dir.parent.name}.{skill_name}.skill"
        importlib.import_module(module_path)

    def load_skill(self, skill_name: str) -> Any:
        """
        动态加载技能

        Args:
            skill_name: 技能名称

        Returns:
            技能实例
        """
        if skill_name in self.skills:
            return self.skills[skill_name]

        # 查找技能目录
        skill_dirs = list(self.skills_dir.glob(f"**/{skill_name}"))
        if not skill_dirs:
            raise ValueError(f"Skill not found: {skill_name}")

        skill_dir = skill_dirs[0]
        skill_file = skill_dir / "skill.py"
        self._load_skill_metadata(skill_name, skill_dir)

        if skill_file.exists():
            self._import_skill_module(skill_dir, skill_name)

        definition = get_skill_definition(skill_name)
        if definition is not None:
            skill_instance = definition.cls()
            self.skills[skill_name] = skill_instance
            return skill_instance

        entrypoint = self.skill_metadata.get(skill_name, {}).get("entrypoint")
        if entrypoint:
            module_name, class_name = entrypoint.split(":", 1)
            module = __import__(module_name, fromlist=[''])
            skill_class = getattr(module, class_name, None)
            if skill_class is None:
                raise ValueError(f"No class found for entrypoint: {entrypoint}")
            skill_instance = skill_class()
            self.skills[skill_name] = skill_instance
            return skill_instance

        if not skill_file.exists():
            md_file = skill_dir / "SKILL.md"
            if not md_file.exists():
                raise ValueError(f"Skill file not found: {skill_file}")
            skill_instance = self._load_markdown_skill(skill_name, md_file)
            self.skills[skill_name] = skill_instance
            return skill_instance

        # 动态导入技能
        spec = __import__(f"SKILLS.{skill_dir.parent.name}.{skill_name}.skill", fromlist=[''])
        skill_class = getattr(spec, skill_name.title().replace('_', ''), None)

        if skill_class is None:
            # 尝试直接获取类
            for attr_name in dir(spec):
                attr = getattr(spec, attr_name)
                if isinstance(attr, type) and hasattr(attr, 'execute'):
                    skill_class = attr
                    break

        if skill_class is None:
            raise ValueError(f"No valid skill class found in {skill_file}")

        skill_instance = skill_class()
        self.skills[skill_name] = skill_instance
        return skill_instance

    def _load_markdown_skill(self, skill_name: str, md_file: Path) -> BaseSkill:
        with open(md_file, 'r', encoding='utf-8') as f:
            md_content = f.read()

        class MarkdownSkill(BaseSkill):
            def __init__(self, name: str, content: str, ai_client: AIClient):
                super().__init__(name)
                self.content = content
                self.ai_client = ai_client

            def execute(self, input_data: SkillInput) -> SkillOutput:
                task_text = input_data.content or input_data.params.get("task", "")
                prompt = (
                    f"技能说明：\n{self.content}\n\n"
                    f"任务：\n{task_text}"
                )

                response = self.ai_client.call_ai(
                    messages=[{"role": "user", "content": prompt}],
                    execution_profile=input_data.execution_profile or "worker_cheap"
                )

                content = self.ai_client.extract_content(response)
                return SkillOutput(success=True, data=content)

        return MarkdownSkill(skill_name, md_content, self.ai_client)

    def _load_skill_metadata(self, skill_name: str, skill_dir: Path) -> None:
        if skill_name in self.skill_metadata:
            return

        meta_file = skill_dir / "skill_meta.yaml"
        if not meta_file.exists():
            self.skill_metadata[skill_name] = {}
            return

        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = yaml.safe_load(f) or {}
        self.skill_metadata[skill_name] = meta

    def get_skill_keywords(self, skill_name: str) -> List[str]:
        if skill_name not in self.skill_metadata:
            skill_dirs = list(self.skills_dir.glob(f"**/{skill_name}"))
            if skill_dirs:
                self._load_skill_metadata(skill_name, skill_dirs[0])
            else:
                self.skill_metadata[skill_name] = {}

        meta = self.skill_metadata.get(skill_name, {})
        keywords = meta.get("keywords")
        if isinstance(keywords, list):
            return [str(k) for k in keywords]
        return DEFAULT_SKILL_KEYWORDS.get(skill_name, [])

    def _render_value(self, value: Any, context: Dict[str, Any]) -> Any:
        if isinstance(value, str):
            def repl(match: re.Match) -> str:
                key = match.group(1)
                return str(context.get(key, match.group(0)))
            return re.sub(r"\{\{(\w+)\}\}", repl, value)
        if isinstance(value, dict):
            return {k: self._render_value(v, context) for k, v in value.items()}
        if isinstance(value, list):
            return [self._render_value(v, context) for v in value]
        return value

    def _render_params(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {k: self._render_value(v, context) for k, v in params.items()}

    def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        加载工作流定义

        Args:
            workflow_name: 工作流名称

        Returns:
            工作流配置字典
        """
        workflow_file = self.workflows_dir / f"{workflow_name}.yaml"

        if not workflow_file.exists():
            raise ValueError(f"Workflow not found: {workflow_name}")

        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)

        return workflow

    @retry_on_failure(max_retries=3, delay=1.0)
    def run_skill(self, skill_name: str, input_data: SkillInput) -> SkillOutput:
        """
        执行单个技能（带重试）

        Args:
            skill_name: 技能名称
            input_data: 技能输入

        Returns:
            技能输出
        """
        skill = self.load_skill(skill_name)

        if not skill.validate_input(input_data):
            return SkillOutput(success=False, error="Invalid input", error_type="validation")

        result = skill.execute(input_data)
        return result

    def execute_workflow(
        self,
        workflow_name: str,
        params: Optional[Dict[str, Any]] = None,
        track: bool = True
    ) -> tuple[str, Dict[str, Any]]:
        """
        执行工作流

        Args:
            workflow_name: 工作流名称
            params: 工作流参数
            track: 是否跟踪任务

        Returns:
            (task_id, result) 任务ID和最终结果
        """
        workflow = self.load_workflow(workflow_name)

        task_id = ""

        if track:
            task_id = self.tracker.create_task(workflow_name, params)

        context = params or {}
        final_result = {}

        for step in workflow.get('steps', []):
            skill_name = step['skill']
            step_params = step.get('params', {})
            rendered_params = self._render_params(step_params, context)
            task_text = (
                context.get("task")
                or context.get("query")
                or context.get("question")
                or ""
            )

            # 合并参数和上下文
            skill_input = SkillInput(
                task_id=task_id,
                sender="router",
                receiver=skill_name,
                role="skill",
                content=str(task_text),
                params={**rendered_params, **context},
                context=context,
                execution_profile=step.get('execution_profile')
            )

            if track:
                self.tracker.update_step(task_id, skill_name, "running")

            result = self.run_skill(skill_name, skill_input)

            if track:
                status = "completed" if result.success else "failed"
                self.tracker.update_step(
                    task_id,
                    skill_name,
                    status,
                    output=result.data if result.success else None,
                    error=result.error
                )

            if not result.success:
                if track:
                    self.tracker.fail_task(task_id, result.error)
                logger.error("Workflow step failed", extra={"workflow": workflow_name, "step": skill_name})
                return (task_id, {"error": result.error, "failed_step": skill_name})

            # 更新上下文
            context.update(result.next_context)
            final_result[skill_name] = result.data

        if track:
            self.tracker.complete_task(task_id, final_result)

        return (task_id, final_result)

    def execute_agent_flow(
        self,
        workflow_name: str,
        params: Optional[Dict[str, Any]] = None,
        track: bool = True
    ) -> tuple[str, Dict[str, Any]]:
        """
        执行多 Agent 串行工作流

        Args:
            workflow_name: 工作流名称
            params: 输入参数（建议包含 task/query/question）
            track: 是否跟踪任务

        Returns:
            (task_id, result) 任务ID和最终结果
        """
        workflow = self.load_workflow(workflow_name)
        if "agents" not in workflow:
            raise ValueError("Workflow is not an agent flow")

        parallel_workers = bool(workflow.get("parallel_workers", False))

        params = params or {}
        task_text = (
            params.get("task")
            or params.get("query")
            or params.get("question")
            or ""
        )

        orchestrator = Orchestrator(
            workflow,
            tracker=self.tracker,
            ai_client=self.ai_client,
            router=self
        )
        return orchestrator.run(
            task_text,
            context=params,
            track=track,
            parallel_workers=parallel_workers
        )

    def list_workflows(self) -> list:
        """列出所有可用的工作流"""
        workflows = []
        for wf_file in self.workflows_dir.glob("*.yaml"):
            with open(wf_file, 'r', encoding='utf-8') as f:
                wf = yaml.safe_load(f)
                steps_value = wf.get("steps") if isinstance(wf, dict) else []
                if steps_value is None:
                    steps_value = []
                workflows.append({
                    "name": wf_file.stem,
                    "description": wf.get("description", ""),
                    "steps": len(steps_value)
                })
        return workflows

    def list_skills(self) -> list:
        """列出所有可用的技能"""
        skills = []
        for skill_dir in self.skills_dir.glob("**/SKILL.md"):
            parent = skill_dir.parent
            try:
                with open(skill_dir, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取第一行作为描述
                    lines = content.split('\n')
                    description = ""
                    for line in lines:
                        if line.startswith("#") or line.strip() == "":
                            continue
                        description = line.strip()
                        break
                    skills.append({
                        "name": parent.name,
                        "description": description,
                        "path": str(parent)
                    })
            except Exception:
                skills.append({
                    "name": parent.name,
                    "description": "",
                    "path": str(parent)
                })
        return skills

    def list_execution_profiles(self) -> list:
        """列出 execution_profile 详情（供 CLI/UI 展示）"""
        return self.ai_client.get_profile_catalog()
