"""
桌面模式主入口
整合 API 服务器、本地任务队列、SQLite 数据库
"""

import os
import sys
import logging
import asyncio
import threading
from pathlib import Path

# 设置环境变量（在导入其他模块之前）
os.environ["APP_MODE"] = "desktop"
os.environ["STORAGE_MODE"] = "local"
os.environ["CACHE_MODE"] = "local"
os.environ["ENABLE_CACHE"] = "true"

# 设置数据库路径
appdata = os.getenv("APPDATA")
if appdata:
    db_dir = os.path.join(appdata, "AudioTuner")
else:
    db_dir = os.path.join(os.path.expanduser("~"), ".audio_tuner")

os.makedirs(db_dir, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(db_dir, 'app.db')}"

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.dirname(current_dir)
worker_dir = os.path.join(os.path.dirname(api_dir), "worker")
sys.path.insert(0, current_dir)
sys.path.insert(0, api_dir)
sys.path.insert(0, worker_dir)

# 现在导入应用模块
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入现有的API模块
from main_sqlite import app as sqlite_app
from local_queue import get_task_queue, register_task
from storage import storage_service

# 导入worker模块用于注册任务
from app.audio_analysis import analyzer
from app.parameter_inversion import ParameterInverter
from app.audio_rendering import renderer

logger = logging.getLogger(__name__)

# 创建桌面版FastAPI应用
app = FastAPI(
    title="Audio Tuner Desktop",
    description="智能音频调音工具 - 桌面版",
    version="1.0.0"
)

# CORS配置（桌面版更宽松）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载SQLite版本的API路由
app.mount("/api", sqlite_app)

# 静态文件服务（前端）
# 在桌面模式下，前端文件位于resources/frontend目录
if os.environ.get("APP_MODE") == "desktop":
    # 桌面打包模式：前端在resources/frontend
    resources_path = os.environ.get("RESOURCES_PATH")
    if resources_path:
        frontend_build_path = os.path.join(resources_path, "frontend")
    else:
        # 尝试从当前位置推断resources路径
        current_file = os.path.abspath(__file__)
        if "resources" in current_file:
            resources_dir = current_file.split("resources")[0] + "resources"
            frontend_build_path = os.path.join(resources_dir, "frontend")
        else:
            frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")
else:
    # 开发模式：使用相对路径
    frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")

if os.path.exists(frontend_build_path):
    static_path = os.path.join(frontend_build_path, "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

# 本地文件服务
@app.get("/files/{file_path:path}")
async def serve_local_file(file_path: str):
    """提供本地存储的文件"""
    try:
        if hasattr(storage_service, '_full_path'):
            full_path = storage_service._full_path(file_path)
            if os.path.exists(full_path):
                return FileResponse(full_path)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error serving file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 本地上传端点
@app.put("/local-uploads/{file_path:path}")
async def upload_local_file(file_path: str, request: Request):
    """处理本地文件上传"""
    try:
        if hasattr(storage_service, '_full_path'):
            full_path = storage_service._full_path(file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 读取请求体并保存
            content = await request.body()
            with open(full_path, 'wb') as f:
                f.write(content)
            
            return {"message": "File uploaded successfully", "object_key": file_path}
        else:
            raise HTTPException(status_code=500, detail="Local storage not available")
    except Exception as e:
        logger.error(f"Error uploading file {file_path}: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

# 前端路由（SPA支持）
@app.get("/")
@app.get("/{path:path}")
async def serve_frontend(path: str = ""):
    """提供前端应用"""
    index_path = os.path.join(frontend_build_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(
            {"message": "Audio Tuner Desktop API", "version": "1.0.0"},
            status_code=200
        )

# 注册音频处理任务
@register_task("process_audio_job")
def process_audio_job(job_id: str, ref_key: str, tgt_key: str, mode: str):
    """音频处理任务（本地版本）"""
    import tempfile
    import os
    from database import get_db
    from models_sqlite import Job
    
    logger.info(f"Starting audio processing job {job_id}")
    
    try:
        # 更新任务状态
        db = next(get_db())
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise Exception(f"Job {job_id} not found")
        
        job.status = "ANALYZING"
        job.progress = 10
        db.commit()
        
        # 下载文件到临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            ref_path = os.path.join(temp_dir, f"ref_{job_id}.wav")
            tgt_path = os.path.join(temp_dir, f"tgt_{job_id}.wav")
            result_path = os.path.join(temp_dir, f"result_{job_id}.wav")
            
            # 下载参考和目标文件
            storage_service.download_file(ref_key, ref_path)
            storage_service.download_file(tgt_key, tgt_path)
            
            # 分析阶段
            job.progress = 30
            db.commit()
            
            ref_features = analyzer.analyze_features(ref_path)
            tgt_features = analyzer.analyze_features(tgt_path)
            
            # 参数反演阶段
            job.status = "INVERTING"
            job.progress = 50
            db.commit()
            
            inverter = ParameterInverter()
            style_params = inverter.invert_parameters(ref_features, tgt_features, mode)
            
            # 渲染阶段
            job.status = "RENDERING"
            job.progress = 70
            db.commit()
            
            metrics = renderer.render_audio(tgt_path, result_path, style_params)
            
            # 上传结果
            job.progress = 90
            db.commit()
            
            result_key = storage_service.generate_object_key(".wav", "results")
            storage_service.upload_file(result_path, result_key, "audio/wav")
            
            # 完成
            job.status = "COMPLETED"
            job.progress = 100
            job.result_key = result_key
            db.commit()
            
            logger.info(f"Audio processing job {job_id} completed successfully")
            return {"result_key": result_key, "metrics": metrics}
            
    except Exception as e:
        logger.error(f"Audio processing job {job_id} failed: {e}")
        
        # 更新失败状态
        try:
            db = next(get_db())
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error = str(e)
                db.commit()
        except:
            pass
        
        raise


class DesktopApp:
    """桌面应用管理器"""
    
    def __init__(self):
        self.server_thread = None
        self.server = None
        self.host = "127.0.0.1"
        self.port = 8080
        
    def start_server(self):
        """启动API服务器"""
        logger.info(f"Starting desktop server on {self.host}:{self.port}")
        
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=False
        )
        
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(target=self.server.run)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        logger.info("Desktop server started")
    
    def stop_server(self):
        """停止API服务器"""
        if self.server:
            self.server.should_exit = True
        if self.server_thread:
            self.server_thread.join(timeout=5)
        logger.info("Desktop server stopped")
    
    def run(self):
        """运行桌面应用"""
        try:
            self.start_server()
            
            # 等待服务器启动
            import time
            time.sleep(2)
            
            # 打开浏览器（可选）
            if os.getenv("OPEN_BROWSER", "true").lower() in ("1", "true", "yes"):
                import webbrowser
                webbrowser.open(f"http://{self.host}:{self.port}")
            
            # 保持运行
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
            
        finally:
            self.stop_server()
            get_task_queue().shutdown()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行桌面应用
    desktop_app = DesktopApp()
    desktop_app.run()
