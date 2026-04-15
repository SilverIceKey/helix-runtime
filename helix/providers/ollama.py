"""
Helix Runtime - Ollama Provider

支持 Ollama API（OpenAI 兼容格式）
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


@ProviderRegistry.register(ProviderType.OLLAMA)
class OllamaProvider(BaseProvider):
    """
    Ollama Provider

    支持本地和远程 Ollama 实例，使用 OpenAI 兼容 API 格式
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base_url = config.base_url.rstrip("/")
        if not self._base_url:
            self._base_url = "http://localhost:11434/v1"

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

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
        发送对话请求到 Ollama
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

        # Ollama 特定参数
        if kwargs.get("options"):
            payload["options"] = kwargs["options"]

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
        使用 Ollama 进行意图检测

        使用结构化 prompt 让模型输出意图类型
        """
        # 构造意图检测 prompt
        intent_prompt = f"""分析以下用户输入，判断其意图。

用户输入: {user_input}

可选意图类型:
- chat: 普通对话/闲聊
- continue: 继续之前的对话（关键词：continue, resume, keep going, 基于以上）
- workflow_document: 文档生成任务（关键词：生成文档, write a document, create report）
- workflow_revision: 修订/修改任务（关键词：修改, revise, 不是, not correct, 重新）
- code_generation: 代码生成任务（关键词：写代码, code, function, python, javascript）
- analysis: 分析任务（关键词：分析, analyze, compare, 解释）
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
            # 如果意图检测失败，返回 UNKNOWN
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Intent detection failed: {str(e)}",
            )

    async def get_models(self) -> List[str]:
        """
        获取 Ollama 可用模型列表
        """
        try:
            base_url = self._base_url.replace("/v1", "")
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            # 如果获取失败，返回配置的默认模型
            return [self.config.model]

    async def health_check(self) -> bool:
        """
        健康检查：检查 Ollama 服务是否可用
        """
        try:
            base_url = self._base_url.replace("/v1", "")
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{base_url}/api/tags")
                return response.status_code == 200
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

        # 尝试从 content 中提取 JSON
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                intent_str = result.get("intent", "unknown")
                confidence = float(result.get("confidence", 0.5))
                reasoning = result.get("reasoning", "")

                # 映射意图字符串到 IntentType
                intent = IntentType(intent_str.lower())

                return IntentResult(
                    intent=intent,
                    confidence=confidence,
                    reasoning=reasoning,
                    suggested_provider=self.provider_type.value,
                )
            except (json.JSONDecodeError, ValueError):
                pass

        # 如果解析失败，使用关键词匹配作为后备
        return self._fallback_intent_detection(user_input)

    def _fallback_intent_detection(self, user_input: str) -> IntentResult:
        """基于关键词的意图检测（后备方案）"""
        user_input_lower = user_input.lower().strip()

        # Continue 检测
        continue_keywords = ["continue", "resume", "keep going", "go on", "继续", "接着"]
        if any(kw in user_input_lower for kw in continue_keywords):
            return IntentResult(
                intent=IntentType.CONTINUE,
                confidence=0.9,
                reasoning="Keyword match: continue/resume",
                suggested_provider=self.provider_type.value,
            )

        # Code generation 检测
        code_keywords = ["code", "function", "python", "javascript", "写代码", "代码"]
        if any(kw in user_input_lower for kw in code_keywords):
            return IntentResult(
                intent=IntentType.CODE_GENERATION,
                confidence=0.8,
                reasoning="Keyword match: code",
                suggested_provider=self.provider_type.value,
            )

        # Document generation 检测
        doc_keywords = ["document", "report", "生成文档", "写文档", "create report"]
        if any(kw in user_input_lower for kw in doc_keywords):
            return IntentResult(
                intent=IntentType.WORKFLOW_DOCUMENT,
                confidence=0.8,
                reasoning="Keyword match: document",
                suggested_provider=self.provider_type.value,
            )

        # Revision 检测
        revision_keywords = ["modify", "revise", "change", "not correct", "修改", "重新", "不对"]
        if any(kw in user_input_lower for kw in revision_keywords):
            return IntentResult(
                intent=IntentType.WORKFLOW_REVISION,
                confidence=0.8,
                reasoning="Keyword match: revision",
                suggested_provider=self.provider_type.value,
            )

        # Default to chat
        return IntentResult(
            intent=IntentType.CHAT,
            confidence=0.5,
            reasoning="Default: no specific intent matched",
            suggested_provider=self.provider_type.value,
        )
