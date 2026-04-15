import logging
import sys
from fastapi import FastAPI
from fastapi.responses import FileResponse
from helix.config import settings
from helix.api.sessions import router as sessions_router
from helix.api.chat import router as chat_router, chat_router as stream_chat_router
from helix.api.workflows import router as workflows_router
from helix.api.config import router as config_router, mcp_router
from helix.mcp.server import mcp_app as mcp_routes

# 配置日志输出到终端
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# 设置 httpx 的日志级别
logging.getLogger("httpx").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用
    """
    app = FastAPI(
        title=settings.app_name,
        description="AI Runtime Infrastructure - 轻量级 AI 应用运行时基础设施",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 注册路由
    app.include_router(sessions_router)
    app.include_router(chat_router)
    app.include_router(stream_chat_router)
    app.include_router(workflows_router)
    app.include_router(config_router)
    app.include_router(mcp_router)

    # 注册 MCP 路由（通过 mounted sub-app）
    app.mount("/mcp", mcp_routes)

    @app.get("/")
    async def root():
        """
        根路径 - 返回前端页面
        """
        from pathlib import Path
        return FileResponse(Path(__file__).parent / "templates" / "index.html")

    @app.get("/health")
    async def health_check():
        """
        健康检查端点
        """
        return {"status": "ok"}

    return app


app = create_app()
