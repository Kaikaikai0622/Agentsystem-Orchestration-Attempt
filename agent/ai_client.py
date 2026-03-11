"""
AI Client - 统一的 AI 调用接口
根据 execution_profile 选择合适的模型
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import requests
import yaml

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .anthropic_client_factory import get_anthropic_client


logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """模型配置"""
    provider: str
    sdk: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    retry_attempts: int
    retry_delay: float
    api_key_env: str
    base_url: str
    purpose: str = ""
    description: str = ""


class AIClient:
    """统一的 AI 客户端"""

    _instances: Dict[str, "AIClient"] = {}

    @classmethod
    def get_instance(cls, config_path: str = "CONFIG/model_registry.yaml") -> "AIClient":
        if config_path not in cls._instances:
            cls._instances[config_path] = cls(config_path)
        return cls._instances[config_path]

    def __init__(self, config_path: str = "CONFIG/model_registry.yaml"):
        self.config_path = config_path
        self.profiles: Dict[str, ModelConfig] = {}
        self.providers: Dict[str, Any] = {}
        self.profile_mapping: Dict[str, str] = {}
        self._load_config()

    def _load_config(self):
        """加载模型配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 加载 execution_profiles
        for name, profile in config['execution_profiles'].items():
            provider_name = config.get('profile_mapping', {}).get(name) or profile.get('provider')
            provider_config = config.get('providers', {}).get(provider_name, {})

            self.profiles[name] = ModelConfig(
                provider=provider_name,
                sdk=provider_config.get('sdk') or self._infer_sdk(provider_name),
                model=profile['model'],
                temperature=profile['temperature'],
                max_tokens=profile['max_tokens'],
                timeout=profile['timeout'],
                retry_attempts=profile['retry_attempts'],
                retry_delay=profile['retry_delay'],
                api_key_env=provider_config.get('api_key_env', ''),
                base_url=provider_config.get('base_url', ''),
                purpose=profile.get('purpose', ''),
                description=profile.get('description', '')
            )

        self.providers = config.get('providers', {})
        self.profile_mapping = config.get('profile_mapping', {})

    def get_model_config(self, execution_profile: str) -> ModelConfig:
        """获取指定 profile 的模型配置"""
        if execution_profile not in self.profiles:
            raise ValueError(f"Unknown execution profile: {execution_profile}")
        return self.profiles[execution_profile]

    @staticmethod
    def _infer_sdk(provider_name: str) -> str:
        if provider_name == "anthropic":
            return "anthropic"
        if provider_name == "moonshot":
            return "openai"
        return "http"

    @staticmethod
    def _resolve_api_key(api_key_env: str) -> Tuple[Optional[str], str]:
        api_key = os.getenv(api_key_env)
        if api_key:
            return api_key, api_key_env

        legacy_fallback_env = {
            "MOONSHOT_API_KEY": "ANTHROPIC_API_KEY"
        }
        fallback_env = legacy_fallback_env.get(api_key_env)
        if fallback_env:
            fallback_key = os.getenv(fallback_env)
            if fallback_key:
                return fallback_key, fallback_env

        return None, api_key_env

    def call_ai(self, messages: List[Dict[str, str]], execution_profile: str = "worker_cheap", **kwargs) -> Dict[str, Any]:
        """
        调用 AI API

        Args:
            messages: 消息列表
            execution_profile: 执行配置
            **kwargs: 额外参数

        Returns:
            API 响应结果（统一格式）
        """
        config = self.get_model_config(execution_profile)
        purpose = f" ({config.purpose})" if config.purpose else ""
        logger.info(
            f"🤖 AI call: profile={execution_profile}{purpose} provider={config.provider} model={config.model}"
        )

        if config.sdk == "anthropic":
            return self._call_anthropic(messages, config, **kwargs)

        if config.sdk == "openai":
            return self._call_openai_sdk(messages, config, **kwargs)

        if config.sdk != "http":
            raise ValueError(f"Unsupported sdk '{config.sdk}' for provider '{config.provider}'")

        api_key, _ = self._resolve_api_key(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for {config.api_key_env}. Please set in .env")

        # 调用 OpenAI 兼容格式的 API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            **kwargs
        }

        response = requests.post(
            f"{config.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=config.timeout
        )

        response.raise_for_status()
        result = response.json()
        result["provider"] = config.provider
        result["sdk"] = "http"

        return result

    def _call_anthropic(self, messages: List[Dict[str, str]], config: ModelConfig, **kwargs) -> Dict[str, Any]:
        api_key, _ = self._resolve_api_key(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for {config.api_key_env}. Please set in .env")

        base_url = config.base_url
        model = config.model
        system_text, clean_messages = self._extract_system(messages)
        client = get_anthropic_client(api_key=api_key, base_url=base_url, timeout=config.timeout)

        call_kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": config.max_tokens,
            "messages": clean_messages,
            "temperature": config.temperature
        }
        if system_text:
            call_kwargs["system"] = system_text

        extra_kwargs = dict(kwargs)
        extra_kwargs.pop("messages", None)
        extra_kwargs.pop("model", None)
        extra_kwargs.pop("system", None)
        call_kwargs.update(extra_kwargs)

        response = client.messages.create(**call_kwargs)
        return self._normalize_anthropic_response(response, model)

    def _call_openai_sdk(self, messages: List[Dict[str, str]], config: ModelConfig, **kwargs) -> Dict[str, Any]:
        if OpenAI is None:
            raise ImportError("openai SDK is not installed. Install openai>=1.0.0 to use openai-sdk providers.")

        api_key, _ = self._resolve_api_key(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for {config.api_key_env}. Please set in .env")

        client = OpenAI(
            api_key=api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )

        call_kwargs: Dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        extra_kwargs = dict(kwargs)
        extra_kwargs.pop("messages", None)
        extra_kwargs.pop("model", None)
        call_kwargs.update(extra_kwargs)

        response = client.chat.completions.create(**call_kwargs)
        result = response.model_dump()
        result["provider"] = config.provider
        result["sdk"] = "openai"
        return result

    @staticmethod
    def _extract_system(messages: List[Dict[str, str]]) -> Tuple[Optional[str], List[Dict[str, str]]]:
        system_parts: List[str] = []
        clean_messages: List[Dict[str, str]] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                if content:
                    system_parts.append(content)
                continue
            clean_messages.append({"role": role, "content": content})

        system_text = "\n\n".join(system_parts) if system_parts else None
        return system_text, clean_messages

    @staticmethod
    def _normalize_anthropic_response(response: Any, model: str) -> Dict[str, Any]:
        text_parts: List[str] = []
        for block in getattr(response, "content", []) or []:
            if getattr(block, "type", "") == "text":
                text_parts.append(block.text)

        content = "\n".join(text_parts)
        usage = getattr(response, "usage", None)
        usage_dict: Dict[str, Any] = {}
        if usage is not None:
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0
            usage_dict = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }

        return {
            "model": getattr(response, "model", None) or model,
            "choices": [{"message": {"content": content}}],
            "usage": usage_dict,
            "provider": "anthropic",
            "sdk": "anthropic",
            "_raw": response
        }

    @staticmethod
    def extract_content(response: Dict[str, Any]) -> str:
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")

    def get_available_profiles(self) -> list:
        """获取可用的 execution_profile 列表"""
        return list(self.profiles.keys())

    def get_profile_catalog(self) -> List[Dict[str, Any]]:
        """获取 execution_profile 详情，供 CLI/UI 展示"""
        catalog: List[Dict[str, Any]] = []
        for name, config in self.profiles.items():
            catalog.append({
                "name": name,
                "purpose": config.purpose,
                "description": config.description,
                "provider": config.provider,
                "model": config.model
            })
        return catalog
