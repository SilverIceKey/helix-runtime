"""
Helix Runtime - DeepSeek Provider

支持 DeepSeek API
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


@ProviderRegistry.register(ProviderType.DEEPSEEK)
class DeepSeekProvider(BaseProvider):
    """
    DeepSeek Provider

    支持 DeepSeek API（OpenAI 兼容格式）
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url.rstrip("/")
        if not self._base_url:
            self._base_url = "https://api.deepseek.com/v1"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.DEEPSEEK

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
        发送对话请求到 DeepSeek
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
        使用 DeepSeek 进行意图检测
        """
        intent_prompt = f"""分析以下用户输入，判断其意图。

用户输入: {user_input}

可选意图类型:
- chat: 普通对话/闲聊
- continue: 继续之前的对话
- workflow_document: 文档生成任务
- workflow_revision: 修订/修改任务
- code_generation: 代码生成任务
- analysis: 分析任务
- unknown: 无法确定的意图

请以 JSON 格式输出：
{{"intent": "意图类型", "confidence": 0.0-1.0, "reasoning": "判断理由"}}
"""

        messages = [
            Message(role="system", content="你是一个意图分析助手。请严格按照指定的 JSON 格式输出。"),
            Message(role="user", content=intent_prompt),
        ]

        try:
            response = await self.chat(messages, temperature=0.3)
            return self._parse_intent_response(response.content, user_input)
        except Exception as e:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Intent detection failed: {str(e)}",
            )

    async def get_models(self) -> List[str]:
        """
        获取 DeepSeek 可用模型列表

        DeepSeek 官方模型列表
        """
        # DeepSeek 官方模型
        return [
            "deepseek-chat",
            "deepseek-coder",
        ]

    async def health_check(self) -> bool:
        """
        健康检查
        """
        try:
            # 发送一个简单的请求来检查连通性
            test_message = [Message(role="user", content="ping")]
            await self.chat(test_message, max_tokens=1)
            return True
        except Exception:
            return False

    def _parse_response(self, data: Dict[str, Any]) -> ChatCompletion:
        """解析 OpenAI 格式的响应"""
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

    def _parse_intent_response(self, content: str, user_input: str) -> IntentResult:
        """解析意图检测响应"""
        import json
        import re

        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                intent_str = result.get("intent", "unknown")
                confidence = float(result.get("confidence", 0.5))
                reasoning = result.get("reasoning", "")
                intent = IntentType(intent_str.lower())

                return IntentResult(
                    intent=intent,
                    confidence=confidence,
                    reasoning=reasoning,
                    suggested_provider=self.provider_type.value,
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # 关键词后备
        return self._fallback_intent_detection(user_input)

    def _fallback_intent_detection(self, user_input: str) -> IntentResult:
        """基于关键词的意图检测"""
        user_input_lower = user_input.lower().strip()

        continue_keywords = ["continue", "resume", "keep going", "继续", "接着"]
        if any(kw in user_input_lower for kw in continue_keywords):
            return IntentResult(IntentType.CONTINUE, 0.9, "Keyword match", self.provider_type.value)

        code_keywords = ["code", "function", "python", "javascript", "写代码", "代码"]
        if any(kw in user_input_lower for kw in code_keywords):
            return IntentResult(IntentType.CODE_GENERATION, 0.8, "Keyword match", self.provider_type.value)

        doc_keywords = ["document", "report", "生成文档", "写文档"]
        if any(kw in user_input_lower for kw in doc_keywords):
            return IntentResult(IntentType.WORKFLOW_DOCUMENT, 0.8, "Keyword match", self.provider_type.value)

        revision_keywords = ["modify", "revise", "not correct", "修改", "重新"]
        if any(kw in user_input_lower for kw in revision_keywords):
            return IntentResult(IntentType.WORKFLOW_REVISION, 0.8, "Keyword match", self.provider_type.value)

        return IntentResult(IntentType.CHAT, 0.5, "Default", self.provider_type.value)
