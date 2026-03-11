"""
Task Tracker - 任务进度跟踪
支持长期任务的持久化和状态查询
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskTracker:
    """任务跟踪器"""

    def __init__(self, memory_dir: str = "MEMORY/tasks"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def create_task(self, workflow_name: str, params: Optional[Dict] = None) -> str:
        """
        创建新任务

        Args:
            workflow_name: 工作流名称
            params: 任务参数

        Returns:
            task_id: 任务ID
        """
        task_id = f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_file = self.memory_dir / f"{task_id}.json"

        task = {
            "task_id": task_id,
            "workflow_name": workflow_name,
            "status": TaskStatus.PENDING.value,
            "current_step": 0,
            "steps": [],
            "params": params or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding='utf-8')
        return task_id

    def update_step(
        self,
        task_id: str,
        step_name: str,
        status: str,
        output: Optional[Any] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        更新任务步骤

        Args:
            task_id: 任务ID
            step_name: 步骤名称
            status: 步骤状态
            output: 输出数据
            error: 错误信息

        Returns:
            是否更新成功
        """
        task_file = self.memory_dir / f"{task_id}.json"
        if not task_file.exists():
            logger.warning("Task file missing", extra={"task_id": task_id})
            return False

        try:
            task = json.loads(task_file.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            # 如果文件编码有问题，跳过更新
            logger.warning("Failed to parse task file", extra={"task_id": task_id})
            return False

        step_index = None
        for i in range(len(task["steps"]) - 1, -1, -1):
            existing = task["steps"][i]
            if existing.get("name") == step_name and existing.get("status") == "running":
                step_index = i
                break

        step = {
            "name": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }

        if output is not None:
            step["output"] = str(output) if not isinstance(output, dict) else output
        if error is not None:
            step["error"] = error

        if step_index is None:
            task["steps"].append(step)
            task["current_step"] = len(task["steps"])
        else:
            task["steps"][step_index] = step
            task["current_step"] = step_index + 1
        task["updated_at"] = datetime.now().isoformat()

        # 更新任务整体状态
        if status == "failed":
            task["status"] = TaskStatus.FAILED.value
        elif task["status"] != TaskStatus.FAILED.value:
            task["status"] = TaskStatus.RUNNING.value

        task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding='utf-8')
        return True

    def complete_task(self, task_id: str, result: Optional[Dict] = None) -> bool:
        """
        标记任务为完成

        Args:
            task_id: 任务ID
            result: 最终结果

        Returns:
            是否更新成功
        """
        task_file = self.memory_dir / f"{task_id}.json"
        if not task_file.exists():
            logger.warning("Task file missing", extra={"task_id": task_id})
            return False

        try:
            task = json.loads(task_file.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            # 如果文件编码有问题，跳过更新
            logger.warning("Failed to parse task file", extra={"task_id": task_id})
            return False

        task["status"] = TaskStatus.COMPLETED.value
        task["completed_at"] = datetime.now().isoformat()
        task["updated_at"] = datetime.now().isoformat()

        if result:
            task["result"] = result

        task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding='utf-8')
        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        """
        标记任务为失败

        Args:
            task_id: 任务ID
            error: 错误信息

        Returns:
            是否更新成功
        """
        task_file = self.memory_dir / f"{task_id}.json"
        if not task_file.exists():
            logger.warning("Task file missing", extra={"task_id": task_id})
            return False

        try:
            task = json.loads(task_file.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            # 如果文件编码有问题，跳过更新
            logger.warning("Failed to parse task file", extra={"task_id": task_id})
            return False

        task["status"] = TaskStatus.FAILED.value
        task["error"] = error
        task["completed_at"] = datetime.now().isoformat()
        task["updated_at"] = datetime.now().isoformat()

        task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False), encoding='utf-8')
        return True

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典
        """
        task_file = self.memory_dir / f"{task_id}.json"
        if task_file.exists():
            try:
                return json.loads(task_file.read_text(encoding='utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning("Failed to parse task file", extra={"task_id": task_id})
                return None
        return None

    def list_tasks(self, workflow_name: Optional[str] = None) -> list:
        """
        列出任务

        Args:
            workflow_name: 筛选特定工作流的任务

        Returns:
            任务列表
        """
        tasks = []
        for task_file in self.memory_dir.glob("*.json"):
            try:
                task = json.loads(task_file.read_text(encoding='utf-8'))
                if workflow_name is None or task.get("workflow_name") == workflow_name:
                    tasks.append(task)
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                # 如果文件编码有问题，跳过
                continue

        # 按创建时间倒序
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return tasks
