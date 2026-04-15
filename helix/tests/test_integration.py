"""
Step 9 - 集成测试

验证以下验收标准：
1. 多轮连续稳定 - 能够连续处理 5 轮以上对话，上下文正确传递
2. 状态正确续接 - 中断后恢复，session state 能够正确续接
3. workflow 可控 - Document Workflow 和 Revision Workflow 能够按预期触发和执行
4. 输入不可变 - 用户原始输入在整个处理流程中保持不变
5. 历史上下文可配置 - MAX_HISTORY_TURNS 可通过配置修改
"""

from fastapi.testclient import TestClient
from helix.main import app
from helix.storage import reset_storage, get_storage


def reset_all():
    """重置所有全局单例"""
    reset_storage()
    # 重置核心模块的全局单例
    import helix.core.capability_trigger as ct
    import helix.core.context_manager as cm
    import helix.core.state_engine as se
    import helix.core.workflow_runtime as wr
    ct._trigger = None
    cm._context_manager = None
    se._state_engine = None
    wr._workflow_runtime = None


def test_multi_round_conversation():
    """
    验收标准 1: 多轮连续稳定
    连续处理 5 轮以上对话，上下文正确传递
    """
    reset_all()
    client = TestClient(app)

    # 创建 Session
    response = client.post("/api/v1/sessions", json={})
    assert response.status_code == 201
    session_id = response.json()["session_id"]

    # 5 轮对话
    messages = [
        "Hello, how are you?",
        "What is Python?",
        "Tell me about FastAPI",
        "How do I deploy it?",
        "Thanks for the help!",
    ]

    for msg in messages:
        response = client.post(
            f"/api/v1/sessions/{session_id}/chat",
            json={"user_input": msg}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["raw_user_input"] == msg

    # 验证消息历史
    response = client.get(f"/api/v1/sessions/{session_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5

    print("✓ 多轮对话测试通过（5 轮）")


def test_state_resume():
    """
    验收标准 2: 状态正确续接
    中断后恢复，session state 能够正确续接
    """
    reset_all()
    client = TestClient(app)

    # 创建 Session
    response = client.post("/api/v1/sessions", json={})
    session_id = response.json()["session_id"]

    # 第一轮对话，触发状态更新
    response = client.post(
        f"/api/v1/sessions/{session_id}/chat",
        json={"user_input": "Start a task"}
    )
    state_after_first = response.json()["session_state"]
    assert state_after_first["task_status"] == "in_progress"

    # 获取 Session 状态（模拟中断后恢复）
    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200
    resumed_state = response.json()["state"]
    assert resumed_state["task_status"] == "in_progress"

    # 执行 workflow（workflow_step 会在此增加）
    response = client.post(
        f"/api/v1/sessions/{session_id}/workflows",
        json={"workflow_type": "document"}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True

    # 验证 workflow_step 增加
    response = client.get(f"/api/v1/sessions/{session_id}")
    state_after_workflow = response.json()["state"]
    assert state_after_workflow["workflow_step"] == 1

    print("✓ 状态续接测试通过")


def test_workflow_trigger():
    """
    验收标准 3: workflow 可控
    Document Workflow 和 Revision Workflow 能够按预期触发和执行
    """
    reset_all()
    client = TestClient(app)

    # 创建 Session
    response = client.post("/api/v1/sessions", json={})
    session_id = response.json()["session_id"]

    # 触发 Document Workflow
    response = client.post(
        f"/api/v1/sessions/{session_id}/chat",
        json={"user_input": "generate a document about Python"}
    )
    assert response.json()["trigger_result"]["trigger_workflow"] == True
    assert response.json()["trigger_result"]["mode"] == "workflow"

    # 执行 Document Workflow
    response = client.post(
        f"/api/v1/sessions/{session_id}/workflows",
        json={"workflow_type": "document"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["step"] == 4  # 4 步骤全部完成

    # 触发 Revision Workflow
    response = client.post(
        f"/api/v1/sessions/{session_id}/workflows",
        json={"workflow_type": "revision"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["step"] == 4

    print("✓ Workflow 触发测试通过")


def test_input_immutability():
    """
    验收标准 4: 输入不可变
    用户原始输入在整个处理流程中保持不变
    """
    reset_all()
    client = TestClient(app)

    # 创建 Session
    response = client.post("/api/v1/sessions", json={})
    session_id = response.json()["session_id"]

    original_input = "This is my ORIGINAL input with SPECIAL chars: !@#$%"

    response = client.post(
        f"/api/v1/sessions/{session_id}/chat",
        json={"user_input": original_input}
    )
    assert response.status_code == 200
    data = response.json()

    # raw_user_input 必须完全一致
    assert data["raw_user_input"] == original_input

    # 在 context_blocks 中也应该保持一致
    context_blocks = data["prompt_context"]["context_blocks"]
    current_input_block = [b for b in context_blocks if "CURRENT INPUT" in b][0]
    assert original_input in current_input_block

    print("✓ 输入不可变测试通过")


def test_context_configurable():
    """
    验收标准 5: 历史上下文可配置
    MAX_HISTORY_TURNS 可通过配置修改
    """
    from helix.config import settings
    from helix.core.context_manager import ContextManager

    # 测试默认配置
    assert settings.max_recent_turns == 5

    # 测试可创建自定义配置的 ContextManager
    custom_manager = ContextManager(max_recent_turns=10)
    assert custom_manager._max_recent_turns == 10

    custom_manager2 = ContextManager(max_recent_turns=3)
    assert custom_manager2._max_recent_turns == 3

    print("✓ 历史上下文可配置测试通过")


def run_all_tests():
    """运行所有集成测试"""
    print("=" * 50)
    print("开始集成测试 - Step 9")
    print("=" * 50)

    test_multi_round_conversation()
    test_state_resume()
    test_workflow_trigger()
    test_input_immutability()
    test_context_configurable()

    print()
    print("=" * 50)
    print("✅ 所有集成测试通过！")
    print("=" * 50)
    print()
    print("验收标准检查清单：")
    print("  ✅ 多轮连续稳定 - 连续 5 轮对话，上下文正确传递")
    print("  ✅ 状态正确续接 - Session 状态正确恢复和续接")
    print("  ✅ workflow 可控 - Document/Revision Workflow 正常触发和执行")
    print("  ✅ 输入不可变 - 用户原始输入保持不变")
    print("  ✅ 历史上下文可配置 - MAX_HISTORY_TURNS 可配置")


if __name__ == "__main__":
    run_all_tests()
