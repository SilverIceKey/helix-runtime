from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from helix.models import WorkflowResult, WorkflowType
from helix.config import settings


class WorkflowStep(str, Enum):
    """工作流步骤"""
    # Document Workflow
    EXTRACT_STRUCTURE = "extract_structure"
    GENERATE_CONTENT = "generate_content"
    REFINE_FORMAT = "refine_format"
    FINALIZE = "finalize"

    # Revision Workflow
    ANALYZE_ISSUE = "analyze_issue"
    MODIFY_PREVIOUS_RESULT = "modify_previous_result"
    VALIDATE_CONSISTENCY = "validate_consistency"
    RETURN_FINAL = "return_final"


class WorkflowRuntime:
    """
    Post Workflow Runtime - 后置工作流运行时

    在主模型无法单步完成任务时补充流程。

    支持的工作流：
    1. Document Workflow - 文档生成
       步骤：extract_structure -> generate_content -> refine_format -> finalize
    2. Revision Workflow - 修订工作流
       步骤：analyze_issue -> modify_previous_result -> validate_consistency -> return_final

    重试策略：MAX_RETRY = 2
    """

    # 工作流步骤定义
    WORKFLOW_STEPS = {
        WorkflowType.DOCUMENT: [
            WorkflowStep.EXTRACT_STRUCTURE,
            WorkflowStep.GENERATE_CONTENT,
            WorkflowStep.REFINE_FORMAT,
            WorkflowStep.FINALIZE,
        ],
        WorkflowType.REVISION: [
            WorkflowStep.ANALYZE_ISSUE,
            WorkflowStep.MODIFY_PREVIOUS_RESULT,
            WorkflowStep.VALIDATE_CONSISTENCY,
            WorkflowStep.RETURN_FINAL,
        ],
    }

    def __init__(self, max_retry: int | None = None):
        """
        初始化 WorkflowRuntime

        Args:
            max_retry: 最大重试次数，默认使用配置值
        """
        self._max_retry = max_retry or settings.max_workflow_retry

    def execute(
        self,
        workflow_type: WorkflowType,
        context: Dict[str, Any],
        step_handlers: Optional[Dict[WorkflowStep, Callable]] = None,
    ) -> WorkflowResult:
        """
        执行工作流

        Args:
            workflow_type: 工作流类型
            context: 工作流上下文
            step_handlers: 可选的步骤处理器映射

        Returns:
            WorkflowResult - 工作流执行结果
        """
        steps = self.WORKFLOW_STEPS.get(workflow_type, [])
        if not steps:
            return WorkflowResult(
                success=False,
                error=f"Unknown workflow type: {workflow_type}",
                step=0,
            )

        # 如果没有提供处理器，使用默认处理器
        if step_handlers is None:
            step_handlers = self._get_default_handlers()

        result = ""
        retry_count = 0

        for i, step in enumerate(steps):
            handler = step_handlers.get(step)
            if handler is None:
                return WorkflowResult(
                    success=False,
                    error=f"No handler for step: {step}",
                    step=i,
                )

            # 执行步骤
            step_result = self._execute_step(
                handler=handler,
                step=step,
                context=context,
                retry_count=retry_count,
            )

            if not step_result["success"]:
                # 尝试重试
                if retry_count < self._max_retry:
                    retry_count += 1
                    continue
                else:
                    return WorkflowResult(
                        success=False,
                        error=step_result["error"],
                        step=i,
                    )

            result = step_result["output"]
            retry_count = 0  # 成功后重置重试计数

        return WorkflowResult(
            success=True,
            output=result,
            step=len(steps),
        )

    def _execute_step(
        self,
        handler: Callable,
        step: WorkflowStep,
        context: Dict[str, Any],
        retry_count: int,
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            handler: 步骤处理器
            step: 工作流步骤
            context: 工作流上下文
            retry_count: 当前重试次数

        Returns:
            包含 success, output/error 的字典
        """
        try:
            output = handler(step, context)
            return {
                "success": True,
                "output": output,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Step {step} failed: {str(e)}",
            }

    def _get_default_handlers(self) -> Dict[WorkflowStep, Callable]:
        """
        获取默认处理器（框架实现，不包含具体 LLM 调用）

        本阶段只实现框架骨架，具体步骤内容用 mock 实现。
        """
        def default_handler(step: WorkflowStep, context: Dict[str, Any]) -> str:
            return f"[{step.value}] Processed"

        handlers: Dict[WorkflowStep, Callable] = {}
        for step in WorkflowStep:
            handlers[step] = default_handler

        return handlers

    def get_workflow_steps(self, workflow_type: WorkflowType) -> List[WorkflowStep]:
        """
        获取指定工作流类型的步骤列表

        Args:
            workflow_type: 工作流类型

        Returns:
            步骤列表
        """
        return self.WORKFLOW_STEPS.get(workflow_type, [])


# 全局单例
_workflow_runtime: Optional[WorkflowRuntime] = None


def get_workflow_runtime() -> WorkflowRuntime:
    """
    获取全局 WorkflowRuntime 实例
    """
    global _workflow_runtime
    if _workflow_runtime is None:
        _workflow_runtime = WorkflowRuntime()
    return _workflow_runtime
