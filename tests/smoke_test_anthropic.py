"""
Smoke test for Anthropic-compatible third-party API.
"""

import os
import anthropic
import yaml


def load_reviewer_provider_config() -> tuple[str, str, str]:
    with open("CONFIG/model_registry.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    profile_mapping = config.get("profile_mapping", {})
    profiles = config.get("execution_profiles", {})
    providers = config.get("providers", {})

    provider_name = profile_mapping.get("reviewer") or profiles.get("reviewer", {}).get("provider")
    if not provider_name:
        raise ValueError("Missing reviewer provider mapping in CONFIG/model_registry.yaml")

    provider = providers.get(provider_name, {})
    api_key_env = provider.get("api_key_env")
    base_url = provider.get("base_url")
    model = profiles.get("reviewer", {}).get("model")

    if not api_key_env or not base_url or not model:
        raise ValueError("Invalid reviewer/provider config in CONFIG/model_registry.yaml")

    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"Missing {api_key_env} in environment")

    return api_key, base_url, model


def main() -> None:
    api_key, base_url, model = load_reviewer_provider_config()

    client = anthropic.Anthropic(auth_token=api_key, base_url=base_url)

    resp = client.messages.create(
        model=model,
        max_tokens=128,
        system="You are a test assistant.",
        messages=[{"role": "user", "content": "Say hello."}]
    )

    text_blocks = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    print("Basic call:", "".join(text_blocks))


if __name__ == "__main__":
    main()
