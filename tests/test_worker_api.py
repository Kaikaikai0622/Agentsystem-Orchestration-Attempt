"""
单独测试 Worker API 的输出长度
"""
import sys
import os
from dotenv import load_dotenv

# 设置 UTF-8 编码（Windows GBK 问题修复）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

from agent.ai_client import AIClient

def test_worker_output_length():
    """测试 Worker API 的输出长度"""
    print("=" * 60)
    print("Worker API 输出长度测试")
    print("=" * 60)

    # 初始化客户端
    client = AIClient()

    # 查看 worker 配置
    try:
        config = client.get_model_config("worker")
        print(f"\nWorker 配置:")
        print(f"  Provider: {config.provider}")
        print(f"  Model: {config.model}")
        print(f"  Max Tokens: {config.max_tokens}")
        print(f"  Timeout: {config.timeout}s\n")
    except Exception as e:
        print(f"获取配置失败: {e}\n")
        return False

    # 测试不同长度的响应
    test_messages = [
        {
            "role": "system",
            "content": "你是任务执行专家。请详细输出分析结果，包括表格、代码和详细说明。"
        },
        {
            "role": "user",
            "content": """请分析以下数据：销售数据中有 1000 条记录，包含产品ID、销售额、销售日期、销售渠道四个字段。
需要你：
1) 分析各渠道的销售趋势
2) 找出销售额最高的产品
3) 计算月度销售增长率

请提供完整的Python代码、分析结果表格和详细说明。"""
        }
    ]

    print("发送测试请求...\n")

    try:
        response = client.call_ai(messages=test_messages, execution_profile="worker")
        content = client.extract_content(response)

        print("=" * 60)
        print("API 调用成功！")
        print("=" * 60)

        # 统计信息
        print(f"\n响应统计:")
        print(f"  - 响应长度: {len(content)} 字符")
        print(f"  - 响应行数: {len(content.split(chr(10)))} 行")
        print(f"  - 使用的模型: {response.get('model', 'unknown')}")

        if 'usage' in response:
            usage = response['usage']
            print(f"  - Token 使用:")
            print(f"    * Prompt Tokens: {usage.get('prompt_tokens', 0)}")
            print(f"    * Completion Tokens: {usage.get('completion_tokens', 0)}")
            print(f"    * Total Tokens: {usage.get('total_tokens', 0)}")

        # 显示完整输出
        print("\n" + "=" * 60)
        print("完整响应内容:")
        print("=" * 60)
        print(content)
        print("\n" + "=" * 60)
        print("响应结束")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\nAPI 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_worker_output_length()
    sys.exit(0 if success else 1)
