#!/usr/bin/env python3
"""
Test worker agent identity response.
"""

from dotenv import load_dotenv

from agent.ai_client import AIClient


def main() -> int:
    load_dotenv()

    question = "你是什么模型？"
    messages = [
        {"role": "system", "content": "你是任务执行专家。"},
        {"role": "user", "content": question},
    ]

    client = AIClient.get_instance()
    response = client.call_ai(messages=messages, execution_profile="worker")
    content = client.extract_content(response)

    print("Model:", response.get("model", "unknown"))
    print("Response:\n", content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
