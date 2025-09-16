#!/usr/bin/env python3
"""
AudioTuner Desktop 可执行文件构建脚本
使用 PyInstaller 构建包含修复的单文件可执行程序
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioTunerBuilder:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.src_dir = self.root_dir / "src"
        self.api_dir = self.root_dir / "api"
        self.worker_dir = self.root_dir / "worker"
        self.frontend_dir = self.root_dir / "frontend"
        self.build_dir = self.root_dir / "build_temp"
        
        # 清理临时构建目录
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
        
        logger.info(f"Root directory: {self.root_dir}")
        logger.info(f"Build directory: {self.build_dir}")
    
    def prepare_frontend(self):
        """准备前端资源"""
        logger.info("Preparing frontend resources...")
        
        frontend_build = self.frontend_dir / "build"
        if not frontend_build.exists():
            logger.warning("Frontend build not found, using existing frontend files")
            # 如果没有构建的前端，复制源文件
            frontend_src = self.frontend_dir / "src"
            if frontend_src.exists():
                shutil.copytree(frontend_src, self.build_dir / "frontend_src")
        else:
            # 复制构建好的前端
            shutil.copytree(frontend_build, self.build_dir / "frontend")
            logger.info("Frontend build copied successfully")
    
    def create_spec_file(self):
        """创建 PyInstaller spec 文件"""
        logger.info("Creating PyInstaller spec file...")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# 项目根目录
root_dir = Path(r"{self.root_dir}")

# 数据文件列表
datas = []

# 添加前端资源
frontend_build = root_dir / "frontend" / "build"
if frontend_build.exists():
    datas.append((str(frontend_build), "frontend"))

# 添加 API 模块
api_dir = root_dir / "api"
if api_dir.exists():
    datas.append((str(api_dir), "api"))

# 添加 worker 模块
worker_dir = root_dir / "worker"
if worker_dir.exists():
    datas.append((str(worker_dir), "worker"))

# 添加其他资源文件
resources = [
    "requirements.txt",
    "README.md",
]

for resource in resources:
    resource_path = root_dir / resource
    if resource_path.exists():
        datas.append((str(resource_path), "."))

# 隐藏导入
hiddenimports = [
    'uvicorn',
    'fastapi',
    'pydantic',
    'pydantic_settings',
    'sqlalchemy',
    'celery',
    'redis',
    'librosa',
    'numpy',
    'scipy',
    'soundfile',
    'pyloudnorm',
    'pedalboard',
    'pyrubberband',
    'psutil',
    'watchdog',
    'requests',
    'aiofiles',
    'python-multipart',
    'jinja2',
    'starlette',
    'anyio',
    'sniffio',
    'h11',
    'click',
    'typing_extensions',
    'packaging',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
    # 桌面应用相关
    'webview',
    'pythonnet',
    'proxy_tools',
    'bottle',
    'clr_loader',
    'tkinter',
    'tkinter.messagebox',
]

a = Analysis(
    [r"{self.src_dir / 'desktop_app.py'}"],
    pathex=[str(root_dir), str(root_dir / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AudioTuner-Desktop-App',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
        
        spec_file = self.root_dir / "audiotuner.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        logger.info(f"Spec file created: {spec_file}")
        return spec_file
    
    def build_executable(self):
        """构建可执行文件"""
        logger.info("Building executable with PyInstaller...")
        
        # 创建 spec 文件
        spec_file = self.create_spec_file()
        
        # 运行 PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_file)
        ]
        
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"PyInstaller failed with return code {result.returncode}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False
        
        logger.info("PyInstaller completed successfully")
        logger.info(f"STDOUT: {result.stdout}")
        
        # 检查生成的可执行文件
        exe_path = self.root_dir / "dist" / "AudioTuner-Desktop-App.exe"
        if exe_path.exists():
            logger.info(f"Executable created successfully: {exe_path}")

            # 复制到根目录，命名为桌面应用版本
            target_path = self.root_dir / "AudioTuner-Desktop-App.exe"
            shutil.copy2(exe_path, target_path)
            logger.info(f"Desktop app executable copied to: {target_path}")

            return True
        else:
            logger.error("Executable not found after build")
            return False
    
    def cleanup(self):
        """清理临时文件"""
        logger.info("Cleaning up temporary files...")
        
        # 清理构建目录
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        # 清理 PyInstaller 生成的文件
        for cleanup_dir in ["build", "__pycache__"]:
            cleanup_path = self.root_dir / cleanup_dir
            if cleanup_path.exists():
                shutil.rmtree(cleanup_path)
        
        # 清理 spec 文件
        spec_file = self.root_dir / "audiotuner.spec"
        if spec_file.exists():
            spec_file.unlink()
        
        logger.info("Cleanup completed")
    
    def build(self):
        """执行完整构建流程"""
        try:
            logger.info("Starting AudioTuner Desktop build process...")
            
            # 准备前端资源
            self.prepare_frontend()
            
            # 构建可执行文件
            success = self.build_executable()
            
            if success:
                logger.info("Build completed successfully!")
                return True
            else:
                logger.error("Build failed!")
                return False
                
        except Exception as e:
            logger.error(f"Build failed with exception: {e}")
            return False
        finally:
            # 清理临时文件
            self.cleanup()

if __name__ == "__main__":
    builder = AudioTunerBuilder()
    success = builder.build()
    sys.exit(0 if success else 1)
