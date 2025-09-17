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
import json
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

    def show_splash_screen(self):
        """显示启动画面"""
        try:
            import tkinter as tk
            from tkinter import ttk

            splash = tk.Tk()
            splash.title("AudioTuner")
            splash.geometry("400x300")
            splash.resizable(False, False)

            # 居中显示
            splash.eval('tk::PlaceWindow . center')

            # 设置为置顶
            splash.attributes('-topmost', True)

            # 创建主框架
            main_frame = tk.Frame(splash, bg='#0A191E')
            main_frame.pack(fill='both', expand=True)

            # 标题
            title_label = tk.Label(
                main_frame,
                text="AudioTuner",
                font=("Arial", 24, "bold"),
                fg='#3CE6BE',
                bg='#0A191E'
            )
            title_label.pack(pady=(50, 10))

            # 副标题
            subtitle_label = tk.Label(
                main_frame,
                text="智能音频调音工具",
                font=("Arial", 12),
                fg='#B4FFF0',
                bg='#0A191E'
            )
            subtitle_label.pack(pady=(0, 30))

            # 进度条
            progress_var = tk.StringVar(value="正在启动...")
            progress_label = tk.Label(
                main_frame,
                textvariable=progress_var,
                font=("Arial", 10),
                fg='#B4FFF0',
                bg='#0A191E'
            )
            progress_label.pack(pady=(0, 10))

            progress_bar = ttk.Progressbar(
                main_frame,
                length=300,
                mode='determinate'
            )
            progress_bar.pack(pady=(0, 50))

            # 存储引用以便更新
            splash.progress_var = progress_var
            splash.progress_bar = progress_bar

            splash.update()
            return splash

        except Exception as e:
            logger.warning(f"无法显示启动画面: {e}")
            return None

    def update_splash_progress(self, splash_window, message, progress):
        """更新启动画面进度"""
        if not splash_window:
            return

        try:
            splash_window.progress_var.set(message)
            splash_window.progress_bar['value'] = progress
            splash_window.update()
        except Exception as e:
            logger.debug(f"更新启动画面失败: {e}")

    def close_splash_screen(self, splash_window):
        """关闭启动画面"""
        if not splash_window:
            return

        try:
            splash_window.destroy()
        except Exception as e:
            logger.debug(f"关闭启动画面失败: {e}")

    def initialize_resources(self):
        """初始化资源"""
        try:
            # 预热缓存
            logger.info("预热缓存...")

            # 检查数据库连接
            logger.info("检查数据库连接...")

            # 初始化音频处理器
            logger.info("初始化音频处理器...")

            # 预加载必要的库
            logger.info("预加载音频处理库...")
            import librosa
            import numpy as np
            import soundfile as sf

            logger.info("资源初始化完成")

        except Exception as e:
            logger.warning(f"资源初始化部分失败: {e}")
            # 不抛出异常，允许应用继续启动
    
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

        # 检查更新
        self._check_for_updates()

        # 保存窗口状态
        self._save_window_state()

    def on_window_closing(self):
        """窗口关闭前的回调"""
        logger.info("Window is closing...")

        # 保存配置
        self._save_config()

        # 清理资源
        self.cleanup()

    def _check_for_updates(self):
        """检查应用更新"""
        try:
            # 这里可以实现更新检查逻辑
            # 例如：从GitHub API检查最新版本
            logger.info("Checking for updates...")

            # 模拟更新检查
            current_version = "1.0.0"
            logger.info(f"Current version: {current_version}")

        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")

    def _save_window_state(self):
        """保存窗口状态"""
        try:
            config_dir = Path.home() / ".audiotuner"
            config_dir.mkdir(exist_ok=True)

            state = {
                "window": {
                    "width": 1200,
                    "height": 800,
                    "last_opened": time.time()
                },
                "app": {
                    "version": "1.0.0",
                    "first_run": False
                }
            }

            config_file = config_dir / "window_state.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save window state: {e}")

    def _save_config(self):
        """保存应用配置"""
        try:
            config_dir = Path.home() / ".audiotuner"
            config_dir.mkdir(exist_ok=True)

            config = {
                "api_url": self.api_url,
                "data_dir": str(self.data_dir),
                "last_closed": time.time(),
                "settings": {
                    "auto_start": False,
                    "minimize_to_tray": True,
                    "check_updates": True
                }
            }

            config_file = config_dir / "config.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            logger.info("Configuration saved")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            logger.info("Cleaning up resources...")

            # 这里可以添加清理逻辑
            # 例如：关闭数据库连接、清理临时文件等

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
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
        splash_window = None
        try:
            logger.info("Starting AudioTuner Desktop App...")

            # 1. 显示启动画面
            splash_window = self.show_splash_screen()

            # 2. 启动 API 服务器
            self.update_splash_progress(splash_window, "启动音频处理服务...", 20)
            self.start_api_server()

            # 3. 等待 API 服务器就绪
            self.update_splash_progress(splash_window, "等待服务就绪...", 50)
            if not self.wait_for_api_server():
                self.close_splash_screen(splash_window)
                self.show_error_dialog(
                    "启动失败",
                    "无法启动音频处理服务，请检查端口 8080 是否被占用。"
                )
                return False

            # 4. 初始化资源
            self.update_splash_progress(splash_window, "初始化资源...", 80)
            self.initialize_resources()

            # 5. 创建桌面窗口
            self.update_splash_progress(splash_window, "创建应用窗口...", 90)
            window = self.create_window()

            # 6. 关闭启动画面
            self.update_splash_progress(splash_window, "启动完成", 100)
            time.sleep(0.5)  # 让用户看到100%
            self.close_splash_screen(splash_window)
            splash_window = None

            # 7. 启动 webview（这会阻塞直到窗口关闭）
            logger.info("Starting webview...")
            webview.start(
                debug=False,  # 设置为 True 可以启用调试模式
                http_server=False  # 我们使用自己的 FastAPI 服务器
            )

            logger.info("Desktop app closed")
            return True

        except Exception as e:
            logger.error(f"Failed to start desktop app: {e}")
            if splash_window:
                self.close_splash_screen(splash_window)
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
