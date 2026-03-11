"""
测试 Reviewer API (MiniMax) 连接
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from agent.ai_client import AIClient

def test_reviewer_api():
    """测试 reviewer profile 的 API 调用"""
    print("=== 测试 Reviewer API (MiniMax) ===\n")

    # 检查 API key
    api_key = os.getenv("MINIMAXI_API_KEY")
    print(f"API Key 存在: {'是' if api_key else '否'}")
    if api_key:
        print(f"API Key 长度: {len(api_key)}\n")

    # 初始化客户端
    client = AIClient()

    # 查看 reviewer 配置
    try:
        config = client.get_model_config("reviewer")
        print(f"Reviewer 配置:")
        print(f"  Provider: {config.provider}")
        print(f"  Model: {config.model}")
        print(f"  Base URL: {config.base_url}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_tokens}")
        print(f"  Timeout: {config.timeout}s")
        print(f"  API Key Env: {config.api_key_env}\n")
    except Exception as e:
        print(f"获取配置失败: {e}\n")
        return False

    # 测试 API 调用
    print("发送测试请求...")
    test_messages = [
        {"role": "system", "content": "你是一个质量审查专家。"},
        {"role": "user", "content": "请回复'测试成功'来确认连接正常。"}
    ]

    try:
        response = client.call_ai(messages=test_messages, execution_profile="reviewer")
        content = client.extract_content(response)

        print(f"\nAPI 调用成功！")
        print(f"响应内容: {content}")
        print(f"使用的模型: {response.get('model', 'unknown')}")
        if 'usage' in response:
            usage = response['usage']
            print(f"Token 使用: {usage.get('total_tokens', 0)}")
        return True

    except Exception as e:
        print(f"\nAPI 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_reviewer_api()
    sys.exit(0 if success else 1)
