"""
桌面版主入口 - 兼容重构后的架构
"""
import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置桌面模式环境变量
os.environ.setdefault("APP_MODE", "desktop")
os.environ.setdefault("STORAGE_MODE", "local")
os.environ.setdefault("CACHE_MODE", "local")

# 设置资源路径
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包环境
    resources_path = sys._MEIPASS
elif os.environ.get('RESOURCES_PATH'):
    # Electron 环境
    resources_path = os.environ['RESOURCES_PATH']
else:
    # 开发环境
    resources_path = str(project_root)

os.environ.setdefault("RESOURCES_PATH", resources_path)

# 设置数据目录
data_dir = os.path.join(os.path.expanduser("~"), ".audio_tuner")
os.makedirs(data_dir, exist_ok=True)
os.environ.setdefault("DATA_DIR", data_dir)

# 强制使用本地 SQLite 数据库（避免桌面模式误连远程 Postgres）
sqlite_db_path = os.path.join(data_dir, "app.db")
# 统一使用正斜杠，避免 SQLAlchemy 在 Windows 下路径解析问题
sqlite_db_uri = f"sqlite:///{sqlite_db_path.replace('\\', '/')}"
os.environ["DATABASE_URL"] = sqlite_db_uri

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(data_dir, "app.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """桌面版主函数"""
    try:
        logger.info("Starting Audio Tuner Desktop Application")
        logger.info(f"Resources path: {resources_path}")
        logger.info(f"Data directory: {data_dir}")
        logger.info(f"Python path: {sys.path[:3]}")
        
        # 导入并启动重构后的主应用
        from src.main import app
        import uvicorn
        
        # 桌面版配置
        host = "127.0.0.1"
        port = 8080
        
        logger.info(f"Starting server on {host}:{port}")
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=False  # 减少日志噪音
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
