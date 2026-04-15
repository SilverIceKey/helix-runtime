from typing import List, Optional, Dict, Any
from helix.models import Session, Message, SessionState, PromptContext, MessageRole
from helix.config import settings


class ContextManager:
    """
    Context Manager - 上下文管理器

    负责历史上下文选择与 Prompt 拼接。

    核心规则：
    1. MAX_RECENT_TURNS = 5（最近历史策略）
    2. 历史优先级：latest_turns > current_topic > last_decision > last_revision
    3. Prompt Layout：system > state > history > current_input
    4. raw_user_input immutable（用户原始输入不可修改）
    """

    def __init__(self, max_recent_turns: int | None = None):
        """
        初始化 ContextManager

        Args:
            max_recent_turns: 最大最近历史轮数，默认使用配置值
        """
        self._max_recent_turns = max_recent_turns or settings.max_recent_turns

    def build_prompt_context(
        self,
        session: Session,
        user_input: str,
        system_prompt: Optional[str] = None,
    ) -> PromptContext:
        """
        构建 Prompt 上下文

        Args:
            session: Session 对象
            user_input: 用户输入（原始输入，不可修改）
            system_prompt: 可选的系统提示

        Returns:
            PromptContext - 包含 context_blocks 和 final_prompt_segments
        """
        context_blocks: List[str] = []
        final_prompt_segments: List[str] = []

        # 1. System Prompt（如果提供）
        if system_prompt:
            context_blocks.append(f"[SYSTEM]\n{system_prompt}")
            final_prompt_segments.append(system_prompt)

        # 2. Session State
        state_block = self._format_state(session.state)
        context_blocks.append(f"[STATE]\n{state_block}")

        # 3. History（按优先级：latest_turns > current_topic > last_decision > last_revision）
        history_block = self._format_history(session)
        context_blocks.append(f"[HISTORY]\n{history_block}")

        # 4. Current Input（保持原始输入不变）
        current_block = self._format_current_input(user_input)
        context_blocks.append(f"[CURRENT INPUT]\n{current_block}")

        # final_prompt_segments 用于实际发送给 LLM
        final_prompt_segments.append(history_block)
        final_prompt_segments.append(current_block)

        return PromptContext(
            context_blocks=context_blocks,
            final_prompt_segments=final_prompt_segments,
        )

    def _format_state(self, state: SessionState) -> str:
        """
        格式化 Session State
        """
        lines = [
            f"session_id: {state.session_id}",
            f"current_topic: {state.current_topic or 'N/A'}",
            f"current_task: {state.current_task or 'N/A'}",
            f"task_status: {state.task_status.value}",
            f"workflow_step: {state.workflow_step}",
            f"last_feedback_type: {state.last_feedback_type.value}",
        ]
        return "\n".join(lines)

    def _format_history(self, session: Session) -> str:
        """
        格式化历史消息

        按优先级选择：
        1. latest_turns - 最近 N 轮
        2. current_topic - 当前主题相关消息
        3. last_decision - 最后决策
        4. last_revision - 最后修订
        """
        messages = session.messages

        if not messages:
            return "(No history)"

        # 优先策略 1: latest_turns（最近 N 轮）
        # 每轮包含 user + assistant 各一条消息
        recent_messages = self._get_recent_messages(messages, self._max_recent_turns)

        # TODO: 后续可以扩展其他优先级策略
        # - current_topic: 同一 topic 的消息
        # - last_decision: 包含决策标记的消息
        # - last_revision: 包含修订标记的消息

        return self._format_messages(recent_messages)

    def _get_recent_messages(
        self,
        messages: List[Message],
        max_turns: int,
    ) -> List[Message]:
        """
        获取最近 N 轮消息

        Args:
            messages: 完整消息列表
            max_turns: 最大轮数

        Returns:
            最近 N 轮的消息列表
        """
        if not messages:
            return []

        # 计算起始位置
        # 每轮 = 1 user + 1 assistant（如果有）
        total_pairs = len(messages) // 2
        start_index = max(0, len(messages) - max_turns * 2)

        return messages[start_index:]

    def _format_messages(self, messages: List[Message]) -> str:
        """
        格式化消息列表为字符串
        """
        if not messages:
            return "(No history)"

        lines = []
        for msg in messages:
            role = msg.role.value.upper()
            lines.append(f"{role}: {msg.content}")

        return "\n".join(lines)

    def _format_current_input(self, user_input: str) -> str:
        """
        格式化当前输入

        注意：raw_user_input immutable，直接返回原始输入
        """
        return f"USER: {user_input}"

    def get_history_summary(
        self,
        session: Session,
        include_last_decision: bool = False,
        include_last_revision: bool = False,
    ) -> Dict[str, Any]:
        """
        获取历史摘要

        Args:
            session: Session 对象
            include_last_decision: 是否包含最后决策
            include_last_revision: 是否包含最后修订

        Returns:
            历史摘要字典
        """
        messages = session.messages
        total = len(messages)

        if total == 0:
            return {
                "total_messages": 0,
                "recent_count": 0,
                "last_message_role": None,
                "last_decision": None if include_last_decision else None,
                "last_revision": None if include_last_revision else None,
            }

        recent = self._get_recent_messages(messages, self._max_recent_turns)
        last_msg = messages[-1]

        return {
            "total_messages": total,
            "recent_count": len(recent),
            "last_message_role": last_msg.role.value,
            "last_message_content": last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content,
        }


# 全局单例
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """
    获取全局 ContextManager 实例
    """
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
