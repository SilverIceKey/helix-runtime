from fastapi import FastAPI
from helix.config import settings
from helix.api.sessions import router as sessions_router
from helix.api.chat import router as chat_router
from helix.api.workflows import router as workflows_router


def create_app() -> FastAPI:
    """
    创建并配置 FastAPI 应用
    """
    app = FastAPI(
        title=settings.app_name,
        description="AI Runtime Infrastructure - 轻量级 AI 应用运行时基础设施",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 注册路由
    app.include_router(sessions_router)
    app.include_router(chat_router)
    app.include_router(workflows_router)

    @app.get("/")
    async def root():
        """
        根路径 - 健康检查
        """
        return {
            "service": settings.app_name,
            "version": "0.1.0",
            "status": "healthy"
        }

    @app.get("/health")
    async def health_check():
        """
        健康检查端点
        """
        return {"status": "ok"}

    return app


app = create_app()
