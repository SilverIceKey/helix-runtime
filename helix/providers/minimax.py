"""
Helix Runtime - Minimax Provider

支持 Minimax API（Code Plan）
"""

import httpx
import hashlib
import time
from typing import List, Optional, Dict, Any
from helix.providers.base import (
    BaseProvider,
    ProviderConfig,
    ProviderType,
    Message,
    ChatCompletion,
    ChatCompletionChoice,
    IntentResult,
    IntentType,
)
from helix.providers.registry import ProviderRegistry


@ProviderRegistry.register(ProviderType.MINIMAX)
class MinimaxProvider(BaseProvider):
    """
    Minimax Provider

    支持 Minimax API（Code Plan 专用）
    API 格式与 OpenAI 略有不同
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url.rstrip("/")
        if not self._base_url:
            self._base_url = "https://api.minimax.chat/v1"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.MINIMAX

    def _generate_auth_header(self) -> Dict[str, str]:
        """
        Minimax 使用特殊的签名认证

        实际实现需要根据 Minimax 的具体 API 文档调整
        """
        # Minimax Code Plan 可能使用不同的认证方式
        # 这里使用 API Key 作为 Bearer Token
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

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
        发送对话请求到 Minimax
        """
        model = model or self.config.model

        payload = {
            "model": model,
            "messages": self._format_messages_for_provider(messages),
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Minimax 特定参数
        if kwargs.get("role_type"):
            payload["role_type"] = kwargs["role_type"]

        headers = self._generate_auth_header()

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_response(data)

    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        """
        使用 Minimax 进行意图检测

        注意：Minimax 主要用于代码生成，意图检测建议使用其他 Provider
        """
        # Minimax 主要用于代码生成任务
        # 这里使用简单的关键词匹配
        return self._fallback_intent_detection(user_input)

    async def get_models(self) -> List[str]:
        """
        获取 Minimax 可用模型列表

        常见模型：abab6.5s-chat, abab6.5-chat 等
        """
        return [
            "abab6.5s-chat",
            "abab6.5-chat",
        ]

    async def health_check(self) -> bool:
        """
        健康检查
        """
        try:
            test_message = [Message(role="user", content="ping")]
            await self.chat(test_message, max_tokens=1)
            return True
        except Exception:
            return False

    def _parse_response(self, data: Dict[str, Any]) -> ChatCompletion:
        """解析 Minimax 响应"""
        choices = []
        for i, choice_data in enumerate(data.get("choices", [])):
            msg_data = choice_data.get("message", {})
            message = Message(
                role=msg_data.get("role", "assistant"),
                content=msg_data.get("content", ""),
            )
            choices.append(ChatCompletionChoice(
                message=message,
                finish_reason=choice_data.get("finish_reason", ""),
                index=i,
            ))

        return ChatCompletion(
            id=data.get("id", ""),
            model=data.get("model", self.config.model),
            choices=choices,
            usage=data.get("usage", {}),
            created=data.get("created", 0),
        )

    def _fallback_intent_detection(self, user_input: str) -> IntentResult:
        """基于关键词的意图检测"""
        user_input_lower = user_input.lower().strip()

        # 代码生成相关关键词
        code_keywords = [
            "code", "function", "python", "javascript", "java", "go", "rust",
            "写代码", "代码", "帮我写", "implement", "class", "def ", "fn ",
            "api", "interface", "algorithm", "sort", "search"
        ]
        if any(kw in user_input_lower for kw in code_keywords):
            return IntentResult(
                intent=IntentType.CODE_GENERATION,
                confidence=0.85,
                reasoning="Keyword match: code generation",
                suggested_provider=self.provider_type.value,
            )

        # 继续对话
        continue_keywords = ["continue", "resume", "keep going", "继续", "接着", "基于以上"]
        if any(kw in user_input_lower for kw in continue_keywords):
            return IntentResult(
                intent=IntentType.CONTINUE,
                confidence=0.7,
                reasoning="Keyword match: continue",
                suggested_provider=self.provider_type.value,
            )

        # 文档生成
        doc_keywords = ["document", "report", "生成文档", "写文档", "create report"]
        if any(kw in user_input_lower for kw in doc_keywords):
            return IntentResult(
                intent=IntentType.WORKFLOW_DOCUMENT,
                confidence=0.7,
                reasoning="Keyword match: document",
                suggested_provider=self.provider_type.value,
            )

        # 默认使用代码生成（Minimax 擅长）
        return IntentResult(
            intent=IntentType.CODE_GENERATION,
            confidence=0.6,
            reasoning="Default: assuming code generation for Minimax",
            suggested_provider=self.provider_type.value,
        )
