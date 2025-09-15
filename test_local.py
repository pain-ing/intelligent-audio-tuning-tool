#!/usr/bin/env python3
"""
本地测试脚本 - 不依赖 Docker 的快速验证
用于验证 API 和 Worker 的基本功能
"""

import os
import sys
import subprocess
import time
import requests
import json
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 8):
        print("❌ 需要 Python 3.8 或更高版本")
        return False
    print(f"✅ Python 版本: {sys.version}")
    return True

def install_dependencies():
    """安装依赖"""
    print("📦 安装 API 依赖...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "api/requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ API 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ API 依赖安装失败: {e}")
        return False
    
    print("📦 安装 Worker 依赖...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "worker/requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Worker 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ Worker 依赖安装失败: {e}")
        return False
    
    return True

def setup_sqlite_env():
    """设置 SQLite 环境变量"""
    os.environ["DB_URL"] = "sqlite:///./test.db"
    os.environ["QUEUE_URL"] = "memory://"  # 内存队列用于测试
    os.environ["S3_ENDPOINT"] = "http://localhost:9000"
    os.environ["S3_ACCESS_KEY"] = "test"
    os.environ["S3_SECRET_KEY"] = "test"
    print("✅ 环境变量设置完成 (SQLite)")

def create_test_database():
    """创建测试数据库"""
    print("🗄️ 创建测试数据库...")
    
    # 添加 api 目录到 Python 路径
    sys.path.insert(0, str(Path("api").absolute()))
    
    try:
        from sqlalchemy import create_engine
        from app.models_sqlite import Base

        engine = create_engine("sqlite:///./test.db")
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库创建完成")
        return True
    except Exception as e:
        print(f"❌ 数据库创建失败: {e}")
        return False

def start_api_server():
    """启动 API 服务器"""
    print("🚀 启动 API 服务器...")
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("api").absolute())
    
    try:
        # 启动 uvicorn 服务器（使用 SQLite 版本）
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "app.main_sqlite:app",
            "--host", "0.0.0.0",
            "--port", "8080",
            "--reload"
        ], cwd="api", env=env)
        
        # 等待服务器启动
        time.sleep(3)
        
        # 检查服务器是否启动
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                print("✅ API 服务器启动成功")
                return process
            else:
                print(f"❌ API 服务器响应异常: {response.status_code}")
                process.terminate()
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ API 服务器连接失败: {e}")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ API 服务器启动失败: {e}")
        return None

def test_api_endpoints():
    """测试 API 端点"""
    print("🧪 测试 API 端点...")
    
    base_url = "http://localhost:8080"
    
    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ /health 端点正常")
        else:
            print(f"❌ /health 端点异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ /health 端点测试失败: {e}")
        return False
    
    # 测试上传签名
    try:
        response = requests.post(f"{base_url}/uploads/sign", 
                               params={"content_type": "audio/wav", "ext": ".wav"})
        if response.status_code == 200:
            print("✅ /uploads/sign 端点正常")
        else:
            print(f"❌ /uploads/sign 端点异常: {response.status_code}")
    except Exception as e:
        print(f"❌ /uploads/sign 端点测试失败: {e}")
    
    # 测试创建任务
    try:
        job_data = {
            "mode": "A",
            "ref_key": "test_ref.wav",
            "tgt_key": "test_tgt.wav"
        }
        response = requests.post(f"{base_url}/jobs", json=job_data)
        if response.status_code == 200:
            job_id = response.json()["job_id"]
            print(f"✅ /jobs 端点正常，任务 ID: {job_id}")
            
            # 测试查询任务
            response = requests.get(f"{base_url}/jobs/{job_id}")
            if response.status_code == 200:
                job_status = response.json()
                print(f"✅ /jobs/{job_id} 端点正常，状态: {job_status['status']}")
            else:
                print(f"❌ /jobs/{job_id} 端点异常: {response.status_code}")
        else:
            print(f"❌ /jobs 端点异常: {response.status_code}")
    except Exception as e:
        print(f"❌ /jobs 端点测试失败: {e}")
    
    return True

def main():
    """主函数"""
    print("🎵 智能音频调音工具 - 本地测试")
    print("=" * 50)
    
    # 检查 Python 版本
    if not check_python_version():
        return
    
    # 安装依赖
    if not install_dependencies():
        print("❌ 依赖安装失败，请手动安装")
        return
    
    # 设置环境
    setup_sqlite_env()
    
    # 创建数据库
    if not create_test_database():
        return
    
    # 启动 API 服务器
    api_process = start_api_server()
    if not api_process:
        return
    
    try:
        # 测试 API
        test_api_endpoints()
        
        print("\n🎉 本地测试完成！")
        print("📝 API 文档: http://localhost:8080/docs")
        print("🔍 健康检查: http://localhost:8080/health")
        print("\n按 Ctrl+C 停止服务器...")
        
        # 保持服务器运行
        api_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 停止服务器...")
        api_process.terminate()
        api_process.wait()
        print("✅ 服务器已停止")

if __name__ == "__main__":
    main()
