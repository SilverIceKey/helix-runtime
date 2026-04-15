"""
Helix Runtime - Provider 注册表

负责 Provider 的注册、获取和管理
"""

from typing import Dict, Type, Optional, List
from helix.providers.base import BaseProvider, ProviderConfig, ProviderType


class ProviderRegistry:
    """
    Provider 注册表

    使用单例模式管理所有 Provider
    """

    _instance: Optional["ProviderRegistry"] = None
    _providers: Dict[str, BaseProvider] = {}
    _provider_classes: Dict[ProviderType, Type[BaseProvider]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
            cls._instance._provider_classes = {}
        return cls._instance

    @classmethod
    def register(cls, provider_type: ProviderType):
        """
        装饰器：注册 Provider 类

        Usage:
            @ProviderRegistry.register(ProviderType.OLLAMA)
            class OllamaProvider(BaseProvider):
                ...
        """
        def decorator(provider_class: Type[BaseProvider]) -> Type[BaseProvider]:
            cls._provider_classes[provider_type] = provider_class
            return provider_class
        return decorator

    @classmethod
    def create(
        cls,
        provider_type: ProviderType,
        config: ProviderConfig,
    ) -> BaseProvider:
        """
        创建 Provider 实例

        Args:
            provider_type: Provider 类型
            config: Provider 配置

        Returns:
            Provider 实例
        """
        if provider_type not in cls._provider_classes:
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_class = cls._provider_classes[provider_type]
        return provider_class(config)

    @classmethod
    def register_instance(cls, name: str, provider: BaseProvider) -> None:
        """
        注册 Provider 实例（用于 Intent Detection 或 User AI）

        Args:
            name: 实例名称（如 "intent_detection", "user_ai"）
            provider: Provider 实例
        """
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> Optional[BaseProvider]:
        """
        获取已注册的 Provider 实例

        Args:
            name: 实例名称

        Returns:
            Provider 实例，如果不存在返回 None
        """
        return cls._providers.get(name)

    @classmethod
    def get_intent_provider(cls) -> Optional[BaseProvider]:
        """获取 Intent Detection Provider"""
        return cls._providers.get("intent_detection")

    @classmethod
    def get_user_provider(cls) -> Optional[BaseProvider]:
        """获取 User AI Provider"""
        return cls._providers.get("user_ai")

    @classmethod
    def set_intent_provider(cls, provider: BaseProvider) -> None:
        """设置 Intent Detection Provider"""
        cls._providers["intent_detection"] = provider

    @classmethod
    def set_user_provider(cls, provider: BaseProvider) -> None:
        """设置 User AI Provider"""
        cls._providers["user_ai"] = provider

    @classmethod
    def list_providers(cls) -> List[str]:
        """列出所有已注册的 Provider 名称"""
        return list(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """清除所有注册的 Provider（主要用于测试）"""
        cls._providers.clear()


# 全局便捷函数

def get_intent_provider() -> Optional[BaseProvider]:
    """获取 Intent Detection Provider"""
    return ProviderRegistry.get_intent_provider()


def get_user_provider() -> Optional[BaseProvider]:
    """获取 User AI Provider"""
    return ProviderRegistry.get_user_provider()


def set_intent_provider(provider: BaseProvider) -> None:
    """设置 Intent Detection Provider"""
    ProviderRegistry.set_intent_provider(provider)


def set_user_provider(provider: BaseProvider) -> None:
    """设置 User AI Provider"""
    ProviderRegistry.set_user_provider(provider)
