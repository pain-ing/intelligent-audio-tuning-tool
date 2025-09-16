"""
重构后的主应用入口
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.core.config import config, AppMode
from src.api.routes import router, audio_tuner_exception_handler
from src.core.exceptions import AudioTunerException


# 配置日志
logging.basicConfig(
    level=logging.INFO if not config.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info(f"Starting {config.app_name} v{config.app_version}")
    logger.info(f"Mode: {config.app_mode.value}")
    logger.info(f"Storage: {config.storage_mode.value}")
    logger.info(f"Cache: {config.cache_mode.value}")
    
    # 启动时的初始化工作
    if config.app_mode == AppMode.DESKTOP:
        await _setup_desktop_mode()
    else:
        await _setup_cloud_mode()
    
    yield
    
    # 关闭时的清理工作
    logger.info("Shutting down application")


async def _setup_desktop_mode():
    """桌面模式初始化"""
    logger.info("Setting up desktop mode")
    
    # 创建数据目录
    data_dir = config.data_dir or os.path.join(os.path.expanduser("~"), ".audio_tuner")
    os.makedirs(data_dir, exist_ok=True)
    
    # 初始化数据库
    try:
        from api.app.database import engine
        from api.app.models_sqlite import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # 启动本地任务队列
    try:
        from api.app.local_queue import get_task_queue
        task_queue = get_task_queue()
        logger.info("Local task queue initialized")
    except Exception as e:
        logger.error(f"Failed to initialize task queue: {e}")


async def _setup_cloud_mode():
    """云端模式初始化"""
    logger.info("Setting up cloud mode")
    
    # 初始化数据库连接
    try:
        from api.app.database import engine
        from api.app.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # 初始化Redis连接
    try:
        from src.services.cache_service import get_cache_service
        cache_service = get_cache_service()
        logger.info("Cache service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize cache: {e}")


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title=config.app_name,
        description="智能音频调音工具",
        version=config.app_version,
        lifespan=lifespan
    )
    
    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.debug else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(router, prefix="/api")

    # 注册异常处理器
    app.add_exception_handler(AudioTunerException, audio_tuner_exception_handler)
    
    # 静态文件服务
    _setup_static_files(app)
    
    # 前端路由
    _setup_frontend_routes(app)
    
    return app


def _setup_static_files(app: FastAPI):
    """设置静态文件服务"""
    if config.app_mode == AppMode.DESKTOP:
        # 桌面模式：从resources目录提供静态文件
        frontend_path = os.path.join(config.resources_path or "", "frontend")
        if os.path.exists(frontend_path):
            static_path = os.path.join(frontend_path, "static")
            if os.path.exists(static_path):
                app.mount("/static", StaticFiles(directory=static_path), name="static")
                logger.info(f"Static files mounted from: {static_path}")
    else:
        # 云端模式：从构建目录提供静态文件
        frontend_path = os.path.join("frontend", "build")
        if os.path.exists(frontend_path):
            static_path = os.path.join(frontend_path, "static")
            if os.path.exists(static_path):
                app.mount("/static", StaticFiles(directory=static_path), name="static")
                logger.info(f"Static files mounted from: {static_path}")


def _setup_frontend_routes(app: FastAPI):
    """设置前端路由"""
    @app.get("/")
    @app.get("/{path:path}")
    async def serve_frontend(path: str = ""):
        """提供前端应用"""
        if config.app_mode == AppMode.DESKTOP:
            frontend_path = os.path.join(config.resources_path or "", "frontend")
        else:
            frontend_path = os.path.join("frontend", "build")
        
        index_path = os.path.join(frontend_path, "index.html")
        
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
            # 如果前端文件不存在，返回API信息
            return {
                "message": f"{config.app_name} API",
                "version": config.app_version,
                "mode": config.app_mode.value,
                "docs": "/docs"
            }
    
    # 文件服务路由（用于本地存储）
    if config.app_mode == AppMode.DESKTOP:
        from src.services.storage_service import LocalStorageService
        
        @app.get("/files/{file_path:path}")
        async def serve_local_file(file_path: str):
            """提供本地存储的文件"""
            try:
                storage_service = LocalStorageService()
                full_path = storage_service._get_full_path(file_path)
                
                if os.path.exists(full_path):
                    return FileResponse(full_path)
                else:
                    raise AudioTunerException(
                        message=f"File not found: {file_path}",
                        status_code=404
                    )
            except Exception as e:
                logger.error(f"Error serving file {file_path}: {e}")
                raise AudioTunerException(
                    message="File service error",
                    status_code=500
                )


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level="info" if not config.debug else "debug"
    )
