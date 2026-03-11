# Agent System - 多 Agent 协作系统

基于技能(Skill)、工作流(Workflow)和多 Agent 协作的可扩展系统，专注于市场情报分析和竞品研究。

## 项目结构

```
AgentSystem/
├── main.py                     # 程序入口
├── .env                        # 🔴 本地配置（不提交）
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略配置
├── requirements.txt            # Python 依赖
├── CONFIG/                     # 系统配置
│   └── model_registry.yaml     # 模型参数配置
├── SKILLS/                     # 技能库
│   └── common/
│       ├── web_search/         # Web 搜索技能（含实现）
│       │   └── skill.py
│       ├── data_analyst/       # 数据分析技能（仅定义）
│       │   └── SKILL.md
│       └── strategy_advisor/   # 战略顾问技能（仅定义）
│           └── SKILL.md
├── WORKFLOWS/                  # 工作流定义
│   ├── simple_qa.yaml          # 简单问答
│   ├── market_intel.yaml       # 市场情报分析
│   └── agent_flow.yaml         # 多 Agent 协作流
├── MEMORY/                     # 知识沉淀
│   ├── tasks/                  # 任务状态（已实现）
│   ├── logs/                   # 开发日志
│   ├── raw_data/               # 原始数据（待实现）
│   ├── structured/             # 结构化数据（待实现）
│   └── reports/                # 分析报告（待实现）
└── agent/                      # 核心模块
    ├── __init__.py
    ├── base.py                 # 基础接口定义
    ├── ai_client.py            # AI 客户端（支持多 Provider）
    ├── anthropic_client_factory.py  # Anthropic 客户端工厂（含缓存）
    ├── agent.py                # Agent 抽象
    ├── orchestrator.py         # 多 Agent 协同调度器
    ├── skill_registry.py      # 装饰器式技能注册表
    ├── task_tracker.py         # 任务跟踪
    ├── router.py               # 工作流路由器
    └── errors.py               # 错误分类体系
```

## 核心模块说明

| 模块 | 说明 |
|------|------|
| `base.py` | 定义 `BaseSkill`, `SkillInput/Output`, `AgentConfig`, `ExecutionInput/Output` 等基础接口 |
| `agent.py` | Agent 类，含 LLM 调用与技能路由（关键词匹配） |
| `orchestrator.py` | Planner-Worker-Reviewer 串行/并行编排调度器 |
| `router.py` | 工作流解析、技能加载、YAML 参数渲染、重试机制 |
| `ai_client.py` | 多 Provider AI 客户端（HTTP/OpenAI SDK/Anthropic SDK） |
| `anthropic_client_factory.py` | Anthropic 客户端工厂（含缓存） |
| `task_tracker.py` | 任务持久化跟踪（JSON 文件） |
| `skill_registry.py` | 装饰器式技能注册表（`@register_skill`） |
| `errors.py` | 错误分类体系 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 API Keys：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Worker API（用于路由、数据清洗、简单任务）
WORKER_API_KEY=your_worker_api_key_here
WORKER_API_BASE=https://api.openai.com/v1
WORKER_MODEL=gpt-4o-mini

# Analyst API（用于深度分析、市场情报）
ANALYST_API_KEY=your_analyst_api_key_here
ANALYST_API_BASE=https://api.openai.com/v1
ANALYST_MODEL=gpt-4o

# MiniMax API（OpenAI 兼容，用于 Reviewer）
MINIMAXI_API_KEY=your_minimaxi_api_key_here

# Moonshot API（用于 Worker，通过 OpenAI SDK）
MOONSHOT_API_KEY=your_moonshot_api_key_here

# 兼容旧变量（将逐步移除）
# ANTHROPIC_API_KEY=your_legacy_worker_key_here

# Anthropic 兼容 API（Reviewer -> MiniMax）
ANTHROPIC_REVIEWER_API_KEY=your_anthropic_reviewer_key_here
```

### 4. 测试 API 连接（可选）

在配置好 API Key 后，运行测试脚本验证连接：

```bash
python test_reviewer_api.py
```

### 3. 运行

```bash
python main.py
```

## 核心概念

### 1. 技能 (Skill)

技能是可复用的独立功能单元，每个技能：
- 继承自 `BaseSkill`
- 实现 `execute()` 方法
- 使用 `SKILL.md` 定义元数据
- 指定 `execution_profile` 选择模型

### 2. 工作流 (Workflow)

工作流是多个技能的编排，使用 YAML 定义：

```yaml
name: "market_intel"
description: "市场情报分析"
steps:
  - skill: "ai_qa"
    execution_profile: "worker_cheap"
    params:
      question: "{{query}}"
```

### 3. 多 Agent 协作

系统支持多 Agent 协作模式，包含三种角色：

| Agent | 角色 | 执行 Profile | 说明 |
|-------|------|-------------|------|
| Planner | 任务规划者 | `planner` | 负责分析用户任务并分解为子任务 |
| Worker | 任务执行者 | `worker` | 执行具体子任务，可调用技能/工作流 |
| Reviewer | 结果审核者 | `reviewer` | 审核执行结果，确保质量 |

执行流程：
```
用户任务 → Planner (规划) → Workers (执行) → Reviewer (审核) → 最终结果
```

### 4. Agent Flow

Agent Flow 是基于多 Agent 协作的工作流，使用 YAML 定义：

```yaml
name: "agent_flow"
description: "多 Agent 协作工作流"
agents:
  planner:
    role: "task_planner"
    system_prompt: "你是一个任务规划专家..."
    execution_profile: "planner"

  workers:
    - role: "data_analyst"
      skills: ["ai_qa", "market_analysis"]
      execution_profile: "worker"
    - role: "researcher"
      skills: ["web_search"]
      execution_profile: "worker"

  reviewer:
    role: "quality_reviewer"
    system_prompt: "你是一个质量审核专家..."
    execution_profile: "reviewer"

flow: ["planner", "workers", "reviewer"]
```

### 5. Execution Profile

定义不同任务类型使用的模型配置：

<!-- AUTO-GENERATED:execution_profiles:start -->
| Profile | 用途 | 说明 | Provider | 推荐模型 |
|---------|------|------|----------|---------|
| `worker_cheap` | 路由、清洗、简单任务 | 低延迟、低成本的通用执行，适合快速判断、轻量处理与结构化清洗。 | MiniMax | MiniMax-M2.5 |
| `analyst_long` | 深度分析、市场情报、报告生成 | 高质量长文本分析与报告生成，适合复杂推理、策略与结论整合。 | MiniMax | MiniMax-M2.1 |
| `planner` | 任务规划（多 Agent） | 负责将用户任务拆解为可执行步骤，输出结构化计划。 | MiniMax | MiniMax-M2.5 |
| `worker` | 任务执行（多 Agent） | 按计划执行子任务，可调用技能与工具，产出中间结果。 | moonshot | kimi-k2.5 |
| `reviewer` | 结果审核（多 Agent） | 复核质量、发现遗漏、修正表达，并汇总最终输出。 | MiniMax | MiniMax-M2.5 |
<!-- AUTO-GENERATED:execution_profiles:end -->

### 配置单一真实来源 (SSOT)

原则：代码与配置是“执行层”的真理，文档是“展示层”的导出。

- 所有配置的权威定义在 `CONFIG/*.yaml`
- README 中的配置表格/示例由脚本从 `CONFIG/` 自动生成（`python scripts/sync_readme.py`）
- CI 中检查 README 与配置是否同步，不同步则构建失败

## 使用示例

### 在代码中执行工作流

```python
from agent import Router

router = Router()

# 执行简单问答
task_id, result = router.execute_workflow(
    "simple_qa",
    params={"question": "什么是市场情报？"}
)

# 执行市场情报分析
task_id, result = router.execute_workflow(
    "market_intel",
    params={"query": "分析竞品 A 的最新动态"}
)
```

### 查询任务状态

```python
from agent import TaskTracker

tracker = TaskTracker()
status = tracker.get_status(task_id)
print(status)
```

### 使用多 Agent 协作（显式调用）

```python
from agent import Router

router = Router()

# 执行多 Agent 协作任务
task_id, result = router.execute_agent_flow(
    "agent_flow",
    params={
        "task": "分析最近一个月的 AI 行业动态"
    }
)
```

### 直接使用 Orchestrator（显式加载工作流）

```python
from agent import Orchestrator, Router

router = Router()
workflow = router.load_workflow("agent_flow")
orchestrator = Orchestrator(workflow, router=router)

# 执行多 Agent 任务
task_id, result = orchestrator.run(
    task="分析最近一个月的 AI 行业动态",
    context={"user_requirements": "重点关注大模型发布"}
)
```

## 扩展开发

### 添加新技能

1. 创建技能目录：
```bash
mkdir -p SKILLS/your_skill
```

2. 创建 `SKILL.md` 定义技能：
```markdown
# Your Skill
execution_profile: worker_cheap
```

3. 创建 `skill.py` 实现技能：
```python
from agent import BaseSkill, SkillInput, SkillOutput

class YourSkill(BaseSkill):
    def __init__(self):
        super().__init__("your_skill")

    def execute(self, input_data: SkillInput) -> SkillOutput:
        # 你的逻辑
        return SkillOutput(success=True, data={"result": "ok"})
```

### 添加新工作流

在 `WORKFLOWS/` 创建新的 YAML 文件。

### 添加新 Agent

1. 在 `agent/` 目录创建新的 Agent 类（或使用 `agent.py` 中的 `Agent` 基类）
2. 在 `WORKFLOWS/agent_flow.yaml` 中配置新 Agent

```python
from agent import Agent, AgentConfig

class CustomAgent(Agent):
    def __init__(self):
        config = AgentConfig(
            name="custom_agent",
            role="custom_role",
            system_prompt="你的系统提示词",
            skills=["skill1", "skill2"],
            execution_profile="worker"
        )
        super().__init__(config)
```

### 添加新的 AI Provider

在 [`CONFIG/model_registry.yaml`](CONFIG/model_registry.yaml) 中添加：

```yaml
providers:
  your_provider:
    api_key_env: YOUR_API_KEY
    base_url: https://api.example.com/v1

execution_profiles:
  your_profile:
    provider: your_provider
    model: your_model_name
    # ... 其他配置

profile_mapping:
  your_profile: your_provider
```

如果 API 格式不是 OpenAI 兼容格式，需要在 [`agent/ai_client.py`](agent/ai_client.py) 中添加适配方法。


## 支持的 AI Provider

| Provider | 说明 | 文档 |
|----------|------|------|
| OpenAI | 标准 OpenAI API | [文档](https://platform.openai.com/docs) |
| Anthropic | Claude API | [文档](https://docs.anthropic.com) |
| Zhipu | 智谱 GLM API | [文档](https://open.bigmodel.cn) |
| Custom | 自定义 OpenAI 兼容 API | - |

## License

MIT License
