#!/usr/bin/env python3
"""
桌面版构建脚本
自动化构建 Windows 安装包的完整流程
"""

import os
import sys
import shutil
import subprocess
import zipfile
import requests
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DesktopBuilder:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.packaging_dir = Path(__file__).parent
        self.build_dir = self.packaging_dir / "build"
        self.dist_dir = self.packaging_dir / "dist"
        
        # 清理构建目录
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
        
        logger.info(f"Root directory: {self.root_dir}")
        logger.info(f"Packaging directory: {self.packaging_dir}")
    
    def build_frontend(self):
        """构建前端"""
        logger.info("Building frontend...")
        
        frontend_dir = self.root_dir / "frontend"
        if not frontend_dir.exists():
            raise Exception("Frontend directory not found")
        
        # 安装依赖
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        
        # 构建
        subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
        
        # 检查构建结果
        build_output = frontend_dir / "build"
        if not build_output.exists():
            raise Exception("Frontend build failed")
        
        logger.info("Frontend build completed")
    
    def download_python_runtime(self):
        """下载 Python 嵌入式运行时"""
        logger.info("Downloading Python runtime...")
        
        python_dir = self.packaging_dir / "python-runtime"
        if python_dir.exists():
            logger.info("Python runtime already exists, skipping download")
            return
        
        # Python 3.11 嵌入式版本
        python_url = "https://www.python.org/ftp/python/3.11.6/python-3.11.6-embed-amd64.zip"
        python_zip = self.build_dir / "python-embed.zip"
        
        # 下载
        logger.info(f"Downloading from {python_url}")
        response = requests.get(python_url, stream=True)
        response.raise_for_status()
        
        with open(python_zip, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 解压
        python_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(python_zip, 'r') as zip_ref:
            zip_ref.extractall(python_dir)
        
        # 配置 Python 路径
        pth_file = python_dir / "python311._pth"
        if pth_file.exists():
            with open(pth_file, 'a') as f:
                f.write("\n../api\n../worker\n")
        
        logger.info("Python runtime downloaded and configured")
    
    def install_python_dependencies(self):
        """安装 Python 依赖"""
        logger.info("Installing Python dependencies...")
        
        python_dir = self.packaging_dir / "python-runtime"
        python_exe = python_dir / "python.exe"
        
        if not python_exe.exists():
            raise Exception("Python runtime not found")
        
        # 安装 pip
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip_script = self.build_dir / "get-pip.py"
        
        response = requests.get(get_pip_url)
        response.raise_for_status()
        
        with open(get_pip_script, 'wb') as f:
            f.write(response.content)
        
        subprocess.run([str(python_exe), str(get_pip_script)], check=True)
        
        # 安装项目依赖
        requirements_files = [
            self.root_dir / "api" / "requirements.txt",
            self.root_dir / "worker" / "requirements.txt"
        ]
        
        for req_file in requirements_files:
            if req_file.exists():
                logger.info(f"Installing dependencies from {req_file}")
                subprocess.run([
                    str(python_exe), "-m", "pip", "install", 
                    "-r", str(req_file), "--no-warn-script-location"
                ], check=True)
        
        logger.info("Python dependencies installed")
    
    def download_ffmpeg(self):
        """下载 FFmpeg"""
        logger.info("Downloading FFmpeg...")
        
        ffmpeg_dir = self.packaging_dir / "ffmpeg"
        if ffmpeg_dir.exists():
            logger.info("FFmpeg already exists, skipping download")
            return
        
        # FFmpeg Windows 构建
        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        ffmpeg_zip = self.build_dir / "ffmpeg.zip"
        
        # 下载
        logger.info(f"Downloading from {ffmpeg_url}")
        response = requests.get(ffmpeg_url, stream=True)
        response.raise_for_status()
        
        with open(ffmpeg_zip, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 解压
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall(self.build_dir)
        
        # 移动到目标目录
        extracted_dirs = [d for d in self.build_dir.iterdir() if d.is_dir() and d.name.startswith("ffmpeg")]
        if extracted_dirs:
            ffmpeg_extracted = extracted_dirs[0]
            ffmpeg_bin = ffmpeg_extracted / "bin"
            if ffmpeg_bin.exists():
                shutil.move(str(ffmpeg_bin), str(ffmpeg_dir))
            else:
                shutil.move(str(ffmpeg_extracted), str(ffmpeg_dir))
        
        logger.info("FFmpeg downloaded")
    
    def install_electron_deps(self):
        """安装 Electron 依赖"""
        logger.info("Installing Electron dependencies...")
        
        subprocess.run(["npm", "install"], cwd=self.packaging_dir, check=True)
        
        logger.info("Electron dependencies installed")
    
    def build_electron_app(self):
        """构建 Electron 应用"""
        logger.info("Building Electron application...")
        
        # 构建
        subprocess.run(["npm", "run", "build-win"], cwd=self.packaging_dir, check=True)
        
        # 检查输出
        if not self.dist_dir.exists():
            raise Exception("Electron build failed")
        
        logger.info("Electron application built successfully")
    
    def create_installer(self):
        """创建安装包"""
        logger.info("Creating installer...")
        
        # electron-builder 已经创建了安装包
        installer_files = list(self.dist_dir.glob("*.exe"))
        
        if not installer_files:
            raise Exception("No installer found")
        
        installer_file = installer_files[0]
        logger.info(f"Installer created: {installer_file}")
        
        # 重命名为更友好的名称
        final_name = f"AudioTuner-Setup-{self.get_version()}.exe"
        final_path = self.dist_dir / final_name
        
        if final_path != installer_file:
            shutil.move(str(installer_file), str(final_path))
        
        logger.info(f"Final installer: {final_path}")
        return final_path
    
    def get_version(self):
        """获取版本号"""
        try:
            package_json = self.packaging_dir / "package.json"
            import json
            with open(package_json) as f:
                data = json.load(f)
                return data.get("version", "1.0.0")
        except:
            return "1.0.0"
    
    def build_all(self):
        """完整构建流程"""
        try:
            logger.info("Starting desktop build process...")
            
            # 1. 构建前端
            self.build_frontend()
            
            # 2. 下载 Python 运行时
            self.download_python_runtime()
            
            # 3. 安装 Python 依赖
            self.install_python_dependencies()
            
            # 4. 下载 FFmpeg
            self.download_ffmpeg()
            
            # 5. 安装 Electron 依赖
            self.install_electron_deps()
            
            # 6. 构建 Electron 应用
            self.build_electron_app()
            
            # 7. 创建安装包
            installer_path = self.create_installer()
            
            logger.info("=" * 50)
            logger.info("BUILD COMPLETED SUCCESSFULLY!")
            logger.info(f"Installer: {installer_path}")
            logger.info(f"Size: {installer_path.stat().st_size / 1024 / 1024:.1f} MB")
            logger.info("=" * 50)
            
            return installer_path
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            raise


if __name__ == "__main__":
    builder = DesktopBuilder()
    builder.build_all()
