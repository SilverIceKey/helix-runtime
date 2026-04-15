"""
Helix Runtime - AI Provider 层

支持多种 AI Provider：
- Ollama（本地/远程）
- DeepSeek
- Minimax（Code Plan）
- 火山引擎（Code Plan）
"""

# 导入所有 Provider（触发注册）
from helix.providers import ollama
from helix.providers import deepseek
from helix.providers import minimax
from helix.providers import volcengine

from helix.providers.base import (
    BaseProvider,
    ProviderConfig,
    ProviderType,
    IntentType,
    IntentResult,
    Message,
    ChatCompletion,
    ChatCompletionChoice,
)
from helix.providers.registry import (
    ProviderRegistry,
    get_intent_provider,
    get_user_provider,
    set_intent_provider,
    set_user_provider,
)

__all__ = [
    # Base
    "BaseProvider",
    "ProviderConfig",
    "ProviderType",
    "IntentType",
    "IntentResult",
    "Message",
    "ChatCompletion",
    "ChatCompletionChoice",
    # Registry
    "ProviderRegistry",
    "get_intent_provider",
    "get_user_provider",
    "set_intent_provider",
    "set_user_provider",
]
