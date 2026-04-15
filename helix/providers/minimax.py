"""
Helix Runtime - Minimax Provider

支持 Minimax Claude Code 协议（/agent/code）
API: https://api.minimaxi.com/anthropic
模型: minimax-2.7, minimax-2.7-highspeed
"""

import httpx
from typing import List, Optional, Dict, Any
from helix.providers.base import (
    BaseProvider,
    ProviderConfig,
    ProviderType,
    ChatMode,
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
    Minimax Provider - Claude Code 协议

    使用 /agent/code 接口
    API 格式与 OpenAI 不同
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url.rstrip("/")
        if not self._base_url:
            self._base_url = "https://api.minimaxi.com/anthropic"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.MINIMAX

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
        发送对话请求到 Minimax Claude Code 接口
        """
        model = model or self.config.model

        # Claude Code 协议格式
        payload = {
            "model": model,
            "messages": self._format_messages_for_provider(messages),
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature:
            payload["temperature"] = temperature

        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self._base_url}/agent/code",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_response(data, model)

    async def detect_intent(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentResult:
        """
        使用 Minimax 进行意图检测
        """
        return self._fallback_intent_detection(user_input)

    async def get_models(self) -> List[str]:
        """
        获取 Minimax 可用模型列表
        """
        return [
            "minimax-2.7",
            "minimax-2.7-highspeed",
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

    def _parse_response(self, data: Dict[str, Any], model: str) -> ChatCompletion:
        """解析 Minimax Claude Code 响应"""
        # 根据实际响应格式调整
        choices = []
        content = ""

        # Claude Code 协议可能返回不同的结构
        if "content" in data:
            if isinstance(data["content"], list):
                for item in data["content"]:
                    if item.get("type") == "text":
                        content = item.get("text", "")
            else:
                content = data.get("content", "")

        message = Message(role="assistant", content=content)
        choices.append(ChatCompletionChoice(
            message=message,
            finish_reason=data.get("stop_reason", "stop"),
            index=0,
        ))

        return ChatCompletion(
            id=data.get("id", ""),
            model=model,
            choices=choices,
            usage=data.get("usage", {}),
            created=data.get("created", 0),
        )

    def _fallback_intent_detection(self, user_input: str) -> IntentResult:
        """基于关键词的意图检测"""
        user_input_lower = user_input.lower().strip()

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

        continue_keywords = ["continue", "resume", "keep going", "继续", "接着", "基于以上"]
        if any(kw in user_input_lower for kw in continue_keywords):
            return IntentResult(
                intent=IntentType.CONTINUE,
                confidence=0.7,
                reasoning="Keyword match: continue",
                suggested_provider=self.provider_type.value,
            )

        doc_keywords = ["document", "report", "生成文档", "写文档", "create report"]
        if any(kw in user_input_lower for kw in doc_keywords):
            return IntentResult(
                intent=IntentType.WORKFLOW_DOCUMENT,
                confidence=0.7,
                reasoning="Keyword match: document",
                suggested_provider=self.provider_type.value,
            )

        return IntentResult(
            intent=IntentType.CODE_GENERATION,
            confidence=0.6,
            reasoning="Default: assuming code generation for Minimax",
            suggested_provider=self.provider_type.value,
        )
