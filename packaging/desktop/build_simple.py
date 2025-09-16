#!/usr/bin/env python3
"""
简化版桌面构建脚本
构建基础的 Electron 应用（不包含嵌入式 Python 运行时）
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleDesktopBuilder:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.packaging_dir = Path(__file__).parent
        self.dist_dir = self.packaging_dir / "dist"
        
        logger.info(f"Root directory: {self.root_dir}")
        logger.info(f"Packaging directory: {self.packaging_dir}")
    
    def check_prerequisites(self):
        """检查构建前提条件"""
        logger.info("Checking prerequisites...")
        
        # 检查前端构建
        frontend_build = self.root_dir / "frontend" / "build"
        if not frontend_build.exists():
            logger.error("Frontend build not found. Please run 'npm run build' in frontend directory first.")
            return False
        
        # 检查 Node.js 和 npm
        try:
            result = subprocess.run(["node", "--version"], check=True, capture_output=True, text=True)
            logger.info(f"Node.js version: {result.stdout.strip()}")
            result = subprocess.run(["npm", "--version"], check=True, capture_output=True, text=True)
            logger.info(f"npm version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Node.js or npm not found: {e}")
            return False

        # 检查 Python
        try:
            result = subprocess.run([sys.executable, "--version"], check=True, capture_output=True, text=True)
            logger.info(f"Python version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Python not found: {e}")
            return False
        
        logger.info("Prerequisites check passed")
        return True
    
    def install_electron_deps(self):
        """安装 Electron 依赖"""
        logger.info("Installing Electron dependencies...")
        
        try:
            subprocess.run(["npm", "install"], cwd=self.packaging_dir, check=True)
            logger.info("Electron dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Electron dependencies: {e}")
            return False
    
    def build_electron_app(self):
        """构建 Electron 应用"""
        logger.info("Building Electron application...")
        
        try:
            # 清理之前的构建
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)
            
            # 构建应用
            subprocess.run(["npm", "run", "pack"], cwd=self.packaging_dir, check=True)
            
            logger.info("Electron application built successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build Electron application: {e}")
            return False
    
    def create_installer(self):
        """创建安装包"""
        logger.info("Creating installer...")
        
        try:
            # 构建 NSIS 安装包
            subprocess.run(["npm", "run", "build-win"], cwd=self.packaging_dir, check=True)
            
            # 检查输出
            if not self.dist_dir.exists():
                raise Exception("No installer found")
            
            installer_files = list(self.dist_dir.glob("*.exe"))
            if not installer_files:
                raise Exception("No .exe installer found")
            
            installer_file = installer_files[0]
            logger.info(f"Installer created: {installer_file}")
            
            # 重命名为更友好的名称
            final_name = f"AudioTuner-Desktop-{self.get_version()}.exe"
            final_path = self.dist_dir / final_name
            
            if final_path != installer_file:
                shutil.move(str(installer_file), str(final_path))
            
            logger.info(f"Final installer: {final_path}")
            return final_path
            
        except Exception as e:
            logger.error(f"Failed to create installer: {e}")
            return None
    
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
            logger.info("Starting simple desktop build process...")
            
            # 1. 检查前提条件
            if not self.check_prerequisites():
                return False
            
            # 2. 安装 Electron 依赖
            if not self.install_electron_deps():
                return False
            
            # 3. 构建 Electron 应用
            if not self.build_electron_app():
                return False
            
            # 4. 创建安装包
            installer_path = self.create_installer()
            if not installer_path:
                return False
            
            logger.info("=" * 50)
            logger.info("BUILD COMPLETED SUCCESSFULLY!")
            logger.info(f"Installer: {installer_path}")
            logger.info(f"Size: {installer_path.stat().st_size / 1024 / 1024:.1f} MB")
            logger.info("=" * 50)
            logger.info("")
            logger.info("📋 Installation Instructions:")
            logger.info("1. Double-click the installer to install Audio Tuner")
            logger.info("2. Make sure Python is installed on the target system")
            logger.info("3. Install Python dependencies: pip install -r api/requirements.txt")
            logger.info("4. Install Worker dependencies: pip install -r worker/requirements.txt")
            logger.info("5. Launch Audio Tuner from desktop shortcut")
            logger.info("")
            logger.info("🔧 System Requirements:")
            logger.info("- Windows 10/11 x64")
            logger.info("- Python 3.8+ (with pip)")
            logger.info("- 4GB RAM minimum")
            logger.info("- 1GB free disk space")
            
            return True
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            return False


if __name__ == "__main__":
    builder = SimpleDesktopBuilder()
    success = builder.build_all()
    sys.exit(0 if success else 1)
