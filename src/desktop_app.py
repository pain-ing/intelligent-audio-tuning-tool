#!/usr/bin/env python3
"""
AudioTuner 桌面应用程序
使用 pywebview 创建原生桌面窗口显示 Web 界面
"""

import os
import sys
import time
import threading
import logging
import webbrowser
from pathlib import Path
import webview
import requests
from contextlib import contextmanager

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioTunerDesktopApp:
    def __init__(self):
        self.api_process = None
        self.api_port = 8080
        self.api_host = "127.0.0.1"
        self.api_url = f"http://{self.api_host}:{self.api_port}"
        self.window = None
        
        # 设置数据目录
        self.setup_data_directory()
        
        logger.info("AudioTuner Desktop App initialized")
    
    def setup_data_directory(self):
        """设置数据目录"""
        import os
        
        # 使用用户目录下的 .audio_tuner 文件夹
        self.data_dir = Path.home() / ".audio_tuner"
        self.data_dir.mkdir(exist_ok=True)
        
        # 设置环境变量
        os.environ["APP_MODE"] = "desktop"
        os.environ["STORAGE_MODE"] = "local"
        os.environ["CACHE_MODE"] = "local"
        os.environ["DATA_DIR"] = str(self.data_dir)
        os.environ["OPEN_BROWSER"] = "false"  # 不自动打开浏览器
        
        logger.info(f"Data directory: {self.data_dir}")
    
    def start_api_server(self):
        """在后台线程中启动 API 服务器"""
        def run_server():
            try:
                logger.info("Starting API server...")
                
                # 导入并启动主应用
                from src.main import app
                import uvicorn
                
                # 配置 uvicorn 日志以避免打包环境中的问题
                log_config = {
                    "version": 1,
                    "disable_existing_loggers": False,
                    "formatters": {
                        "default": {
                            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        },
                    },
                    "handlers": {
                        "default": {
                            "formatter": "default",
                            "class": "logging.StreamHandler",
                            "stream": "ext://sys.stdout",
                        },
                    },
                    "root": {
                        "level": "INFO",
                        "handlers": ["default"],
                    },
                }
                
                uvicorn.run(
                    app,
                    host=self.api_host,
                    port=self.api_port,
                    log_level="info",
                    access_log=False,
                    log_config=log_config
                )
                
            except Exception as e:
                logger.error(f"Failed to start API server: {e}")
                raise
        
        # 在后台线程中启动服务器
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        logger.info("API server thread started")
    
    def wait_for_api_server(self, max_attempts=30, delay=1):
        """等待 API 服务器启动"""
        logger.info("Waiting for API server to be ready...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{self.api_url}/", timeout=2)
                if response.status_code == 200:
                    logger.info("API server is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            logger.debug(f"API server check attempt {attempt + 1}/{max_attempts}")
            time.sleep(delay)
        
        logger.error("API server failed to start within timeout")
        return False
    
    def create_window(self):
        """创建桌面应用窗口"""
        logger.info("Creating desktop window...")
        
        # 创建 webview 窗口
        self.window = webview.create_window(
            title="AudioTuner - 智能音频调音工具",
            url=self.api_url,
            width=1200,
            height=800,
            min_size=(800, 600),
            resizable=True,
            fullscreen=False,
            minimized=False,
            on_top=False,
            shadow=True,
            focus=True
        )
        
        logger.info("Desktop window created")
        return self.window
    
    def on_window_loaded(self):
        """窗口加载完成后的回调"""
        logger.info("Window loaded successfully")
        
        # 可以在这里添加一些初始化逻辑
        # 例如：检查更新、显示欢迎消息等
    
    def on_window_closing(self):
        """窗口关闭前的回调"""
        logger.info("Window is closing...")
        
        # 清理资源
        # API 服务器会随着主进程退出而自动停止
    
    def show_error_dialog(self, title, message):
        """显示错误对话框"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            messagebox.showerror(title, message)
            root.destroy()
        except ImportError:
            # 如果 tkinter 不可用，输出到控制台
            logger.error(f"{title}: {message}")
    
    def run(self):
        """运行桌面应用程序"""
        try:
            logger.info("Starting AudioTuner Desktop App...")
            
            # 1. 启动 API 服务器
            self.start_api_server()
            
            # 2. 等待 API 服务器就绪
            if not self.wait_for_api_server():
                self.show_error_dialog(
                    "启动失败", 
                    "无法启动音频处理服务，请检查端口 8080 是否被占用。"
                )
                return False
            
            # 3. 创建桌面窗口
            window = self.create_window()
            
            # 4. 启动 webview（这会阻塞直到窗口关闭）
            logger.info("Starting webview...")
            webview.start(
                debug=False,  # 设置为 True 可以启用调试模式
                http_server=False  # 我们使用自己的 FastAPI 服务器
            )
            
            logger.info("Desktop app closed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start desktop app: {e}")
            self.show_error_dialog(
                "启动错误", 
                f"桌面应用启动失败：{str(e)}"
            )
            return False

def main():
    """主函数"""
    try:
        # 创建并运行桌面应用
        app = AudioTunerDesktopApp()
        success = app.run()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
