"""
Helix Runtime - 火山引擎 Provider

支持火山引擎 Doubao API（OpenAI 兼容 /v1/chat/completions）
API: https://ark.cn-beijing.volces.com/api/v3
"""

import httpx
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


@ProviderRegistry.register(ProviderType.VOLCENGINE)
class VolcEngineProvider(BaseProvider):
    """
    火山引擎 Provider - Doubao

    使用 OpenAI 兼容接口 /v1/chat/completions
    API: https://ark.cn-beijing.volces.com/api/v3
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url.rstrip("/")
        if not self._base_url:
            self._base_url = "https://ark.cn-beijing.volces.com/api/coding/v3"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.VOLCENGINE

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
        发送对话请求到火山引擎
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

        headers = self._build_headers()

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
        使用火山引擎进行意图检测
        """
        return self._fallback_intent_detection(user_input)

    async def get_models(self) -> List[str]:
        """
        获取火山引擎可用模型列表
        注意：火山引擎 Ark 需要使用接入点 ID (ep-xxxxx)，而不是直接的模型名称
        请在火山引擎控制台创建接入点后，将接入点 ID 填入模型字段
        """
        return [
            "ep-xxxxxx（请替换为您的接入点ID）",
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
        """解析火山引擎响应"""
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
            reasoning="Default: assuming code generation for VolcEngine",
            suggested_provider=self.provider_type.value,
        )
