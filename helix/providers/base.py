"""
Helix Runtime - AI Provider 抽象层

统一的 AI Provider 接口，支持多种后端：
- Ollama（OpenAI 兼容 /v1/chat/completions）
- DeepSeek（OpenAI 兼容 /v1/chat/completions）
- Minimax Claude Code 协议（/agent/code）
- 火山引擎 Doubao（/v1/chat/completions）

接口类型：
- OpenAI Compatible: POST /v1/chat/completions
- Claude Code: POST /agent/code
- Responses: POST /v1/responses
- Planner: POST /plan/create
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum


class ProviderType(str, Enum):
    """Provider 类型"""
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"
    VOLCENGINE = "volcengine"


class IntentType(str, Enum):
    """意图类型"""
    CHAT = "chat"
    CONTINUE = "continue"
    WORKFLOW_DOCUMENT = "workflow_document"
    WORKFLOW_REVISION = "workflow_revision"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    UNKNOWN = "unknown"


class ChatMode(str, Enum):
    """Chat 接口模式"""
    OPENAI_CHAT = "openai_chat"  # /v1/chat/completions
    RESPONSES = "responses"  # /v1/responses
    CLAUDE_CODE = "claude_code"  # /agent/code
    PLANNER = "planner"  # /plan/create


@dataclass
class Message:
    """消息结构"""
    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class ChatCompletionChoice:
    """Chat Completion 选择"""
    message: Message
    finish_reason: str
    index: int = 0


@dataclass
class ChatCompletion:
    """Chat Completion 响应"""
    id: str
    model: str
    choices: List[ChatCompletionChoice]
    usage: Dict[str, int] = field(default_factory=dict)
    created: int = 0

    @property
    def content(self) -> str:
        return self.choices[0].message.content if self.choices else ""


@dataclass
class IntentResult:
    """意图检测结果"""
    intent: IntentType
    confidence: float
    reasoning: str
    suggested_provider: Optional[str] = None


@dataclass
class ProviderConfig:
    """Provider 配置"""
    type: ProviderType
    model: str
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3
    chat_mode: ChatMode = ChatMode.OPENAI_CHAT  # 接口模式


class BaseProvider(ABC):
    """
    AI Provider 抽象基类

    所有 Provider 必须实现以下接口：
    - chat(): 发送对话请求
    - detect_intent(): 检测用户意图
    - get_models(): 获取可用模型列表
    - health_check(): 健康检查
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client: Optional[Any] = None

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> ChatCompletion:
        """
        发送对话请求

        Args:
            messages: 消息列表
            model: 模型名称（None 使用默认）
            temperature: 温度参数
            max_tokens: 最大 token 数
            stream: 是否流式返回

        Returns:
            ChatCompletion 响应
        """
        pass

    @abstractmethod
    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        """
        检测用户意图

        Args:
            user_input: 用户输入
            context: 上下文信息（可选）

        Returns:
            IntentResult 意图检测结果
        """
        pass

    @abstractmethod
    async def get_models(self) -> List[str]:
        """
        获取可用模型列表

        Returns:
            模型名称列表
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        pass

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """返回 Provider 类型"""
        pass

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _format_messages_for_provider(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """将 Message 列表转换为 Provider 需要的格式"""
        return [msg.to_dict() for msg in messages]
