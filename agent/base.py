"""
Base definitions for the Agent System
定义技能的标准接口和数据结构
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .ai_client import AIClient


@dataclass
class ExecutionInput:
    """统一的执行输入协议"""
    task_id: str = ""
    sender: str = ""
    receiver: str = ""
    role: str = ""
    content: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    attachments: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_profile: Optional[str] = None


@dataclass
class SkillInput(ExecutionInput):
    """技能输入的标准格式"""
    pass


@dataclass
class ExecutionOutput:
    """统一的执行输出协议"""
    task_id: str = ""
    sender: str = ""
    receiver: str = ""
    role: str = ""
    content: str = ""
    success: bool = True
    data: Any = None  # 执行结果数据
    error: Optional[str] = None  # 错误信息
    error_type: Optional[str] = None  # 结构化错误类型
    next_context: Dict[str, Any] = field(default_factory=dict)  # 传给下一个步骤的上下文
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据（执行时间、token使用等）


@dataclass
class SkillOutput(ExecutionOutput):
    """技能输出的标准格式"""
    pass


class BaseSkill:
    """所有技能的基类"""

    def __init__(self, name: str):
        self.name = name

    def execute(self, input_data: SkillInput) -> SkillOutput:
        """
        执行技能，子类必须实现此方法

        Args:
            input_data: 技能输入数据

        Returns:
            SkillOutput: 技能执行结果
        """
        raise NotImplementedError(f"Skill {self.name} must implement execute()")

    def validate_input(self, input_data: SkillInput) -> bool:
        """
        验证输入数据，子类可以重写

        Args:
            input_data: 技能输入数据

        Returns:
            bool: 输入是否有效
        """
        return True


@dataclass
class AgentConfig:
    """Agent configuration"""
    name: str
    role: str
    system_prompt: str
    execution_profile: str
    skills: List[str] = field(default_factory=list)
    ai_client: Optional["AIClient"] = None
