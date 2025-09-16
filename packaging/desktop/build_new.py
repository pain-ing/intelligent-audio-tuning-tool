#!/usr/bin/env python3
"""
新的简化桌面版构建脚本
处理Electron文件锁定问题
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NewDesktopBuilder:
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent
        self.packaging_dir = Path(__file__).parent
        
        logger.info(f"Root directory: {self.root_dir}")
        logger.info(f"Packaging directory: {self.packaging_dir}")
    
    def kill_electron_processes(self):
        """终止可能的Electron进程"""
        logger.info("Checking for running Electron processes...")
        try:
            subprocess.run(["taskkill", "/F", "/IM", "electron.exe"], 
                         capture_output=True, check=False)
            subprocess.run(["taskkill", "/F", "/IM", "AudioTuner*.exe"], 
                         capture_output=True, check=False)
            time.sleep(3)  # 等待进程完全终止
        except Exception as e:
            logger.warning(f"Failed to kill processes: {e}")
    
    def clean_build_dirs(self):
        """清理构建目录"""
        logger.info("Cleaning build directories...")
        
        dirs_to_clean = [
            "node_modules",
            "dist",
            "dist_rf5", 
            "out_build",
            "release"
        ]
        
        for dir_name in dirs_to_clean:
            dir_path = self.packaging_dir / dir_name
            if dir_path.exists():
                logger.info(f"Removing {dir_name}...")
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    logger.warning(f"Failed to remove {dir_name}: {e}")
                    # 尝试使用系统命令强制删除
                    try:
                        subprocess.run(["rmdir", "/S", "/Q", str(dir_path)], 
                                     shell=True, check=False)
                    except:
                        pass
        
        # 删除锁定文件
        lock_files = ["package-lock.json", "yarn.lock"]
        for lock_file in lock_files:
            lock_path = self.packaging_dir / lock_file
            if lock_path.exists():
                try:
                    lock_path.unlink()
                    logger.info(f"Removed {lock_file}")
                except:
                    pass
    
    def install_electron_deps(self):
        """安装 Electron 依赖"""
        logger.info("Installing Electron dependencies...")
        
        # 使用更简单的安装方式
        try:
            # 尝试使用yarn（通常更稳定）
            result = subprocess.run(["yarn", "--version"], capture_output=True, check=True)
            logger.info("Using yarn for installation...")
            subprocess.run(["yarn", "install", "--ignore-engines"], 
                         cwd=self.packaging_dir, check=True)
        except:
            logger.info("Using npm for installation...")
            subprocess.run(["npm", "install", "--no-package-lock", "--legacy-peer-deps", "--force"], 
                         cwd=self.packaging_dir, check=True)
        
        logger.info("Electron dependencies installed")
    
    def build_electron_app(self):
        """构建 Electron 应用"""
        logger.info("Building Electron application...")
        
        # 检查前端构建是否存在
        frontend_build = self.root_dir / "frontend" / "build"
        if not frontend_build.exists():
            raise Exception("Frontend build not found. Please run 'npm run build' in frontend directory first.")
        
        # 构建
        try:
            subprocess.run(["npm", "run", "build"], cwd=self.packaging_dir, check=True)
        except:
            # 如果npm失败，尝试yarn
            try:
                subprocess.run(["yarn", "build"], cwd=self.packaging_dir, check=True)
            except:
                # 最后尝试直接调用electron-builder
                subprocess.run(["npx", "electron-builder", "--win", "portable", "--publish=never"], 
                             cwd=self.packaging_dir, check=True)
        
        # 检查输出
        possible_dist_dirs = ["dist_rf5", "dist", "release"]
        dist_dir = None
        
        for dir_name in possible_dist_dirs:
            test_dir = self.packaging_dir / dir_name
            if test_dir.exists():
                dist_dir = test_dir
                break
        
        if not dist_dir:
            raise Exception("Electron build failed - no output directory found")
        
        logger.info(f"Electron application built successfully in {dist_dir}")
        return dist_dir
    
    def find_installer(self, dist_dir):
        """查找生成的安装包"""
        installer_files = list(dist_dir.glob("*.exe"))
        
        if not installer_files:
            # 检查子目录
            for subdir in dist_dir.iterdir():
                if subdir.is_dir():
                    installer_files.extend(subdir.glob("*.exe"))
        
        if not installer_files:
            raise Exception("No installer found")
        
        installer_file = installer_files[0]
        logger.info(f"Installer found: {installer_file}")
        
        return installer_file
    
    def build_all(self):
        """完整构建流程"""
        try:
            logger.info("Starting new desktop build process...")
            
            # 1. 终止可能的进程
            self.kill_electron_processes()
            
            # 2. 清理构建目录
            self.clean_build_dirs()
            
            # 3. 安装 Electron 依赖
            self.install_electron_deps()
            
            # 4. 构建 Electron 应用
            dist_dir = self.build_electron_app()
            
            # 5. 查找安装包
            installer_path = self.find_installer(dist_dir)
            
            logger.info("=" * 50)
            logger.info("BUILD COMPLETED SUCCESSFULLY!")
            logger.info(f"Installer: {installer_path}")
            logger.info(f"Size: {installer_path.stat().st_size / 1024 / 1024:.1f} MB")
            logger.info("=" * 50)
            
            return installer_path
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    builder = NewDesktopBuilder()
    builder.build_all()
