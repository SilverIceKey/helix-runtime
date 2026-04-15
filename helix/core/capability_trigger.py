from helix.models.trigger import TriggerResult, UserRequest
from helix.config import settings
import re


class CapabilityTrigger:
    """
    Capability Trigger Layer - 能力触发层

    决定当前请求是否需要触发特定系统能力。

    支持两种触发类型：
    1. Context Trigger - 上下文续接触发
    2. Workflow Trigger - 工作流触发
    """

    # Context Trigger 关键词（不区分大小写）
    CONTEXT_TRIGGER_PATTERNS = [
        r"^continue\s*$",
        r"^continue\s+previous",
        r"^based\s+on\s+above",
        r"^modify\s+previous",
        r"^not\s+correct",
        r"^continue\s+where\s+we\s+left",
        r"^keep\s+going",
        r"^go\s+on",
        r"^resume",
    ]

    # Workflow Trigger 关键词（不区分大小写）
    WORKFLOW_TRIGGER_PATTERNS = [
        r"document\s+generation",
        r"multi[- ]step\s+analysis",
        r"revision\s+task",
        r"formatting\s+task",
        r"generate\s+a?\s*document",
        r"write\s+a?\s*report",
        r"create\s+a?\s*summary",
        r"analyze\s+this",
        r"help\s+me\s+revise",
        r"format\s+this",
    ]

    def __init__(self):
        self._context_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.CONTEXT_TRIGGER_PATTERNS
        ]
        self._workflow_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.WORKFLOW_TRIGGER_PATTERNS
        ]

    def evaluate(self, user_input: str) -> TriggerResult:
        """
        评估用户输入，决定是否触发能力

        Args:
            user_input: 用户输入文本

        Returns:
            TriggerResult - 包含触发判断结果
        """
        trigger_context = self._check_context_trigger(user_input)
        trigger_workflow = self._check_workflow_trigger(user_input)

        # 确定模式
        if trigger_context and trigger_workflow:
            # 两者都触发时，优先 workflow
            mode = "workflow"
        elif trigger_context:
            mode = "continue"
        elif trigger_workflow:
            mode = "workflow"
        else:
            mode = "direct"

        return TriggerResult(
            trigger_context=trigger_context,
            trigger_workflow=trigger_workflow,
            mode=mode,
        )

    def _check_context_trigger(self, user_input: str) -> bool:
        """
        检查是否触发 Context Trigger

        Context Trigger 用于多轮对话续接场景。
        """
        if not user_input or not user_input.strip():
            return False

        text = user_input.strip().lower()
        for pattern in self._context_patterns:
            if pattern.match(text):
                return True
        return False

    def _check_workflow_trigger(self, user_input: str) -> bool:
        """
        检查是否触发 Workflow Trigger

        Workflow Trigger 用于文档生成、多步分析等需要后置工作流的场景。
        """
        if not user_input or not user_input.strip():
            return False

        text = user_input.strip().lower()
        for pattern in self._workflow_patterns:
            if pattern.search(text):
                return True
        return False

    def add_context_pattern(self, pattern: str) -> None:
        """
        动态添加 Context Trigger 模式

        Args:
            pattern: 正则表达式模式
        """
        self._context_patterns.append(re.compile(pattern, re.IGNORECASE))

    def add_workflow_pattern(self, pattern: str) -> None:
        """
        动态添加 Workflow Trigger 模式

        Args:
            pattern: 正则表达式模式
        """
        self._workflow_patterns.append(re.compile(pattern, re.IGNORECASE))


# 全局单例
_trigger: CapabilityTrigger | None = None


def get_trigger() -> CapabilityTrigger:
    """
    获取全局 CapabilityTrigger 实例
    """
    global _trigger
    if _trigger is None:
        _trigger = CapabilityTrigger()
    return _trigger
