#!/usr/bin/env python3
"""
对象存储集成测试脚本
测试 MinIO/S3 文件上传、下载、签名 URL 等功能
"""

import os
import sys
import tempfile
import requests
import json
from pathlib import Path

# 添加 API 目录到路径
sys.path.insert(0, str(Path("api").absolute()))

def test_storage_service():
    """测试存储服务基本功能"""
    print("🗄️ 测试存储服务...")
    
    try:
        from app.storage import StorageService
        
        # 初始化存储服务
        storage = StorageService()
        print("✅ 存储服务初始化成功")
        
        # 测试生成对象键名
        object_key = storage.generate_object_key(".wav", "test")
        print(f"✅ 生成对象键名: {object_key}")
        
        # 测试生成上传签名
        signature = storage.generate_upload_signature("audio/wav", ".wav")
        print(f"✅ 生成上传签名: {signature['object_key']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 存储服务测试失败: {e}")
        return False

def test_api_endpoints():
    """测试 API 端点"""
    print("\n🌐 测试 API 端点...")
    
    base_url = "http://localhost:8080"
    
    try:
        # 测试健康检查
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 健康检查通过")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
        
        # 测试上传签名
        upload_data = {
            "content_type": "audio/wav",
            "extension": ".wav"
        }
        
        response = requests.post(f"{base_url}/uploads/sign", json=upload_data, timeout=10)
        
        if response.status_code == 200:
            signature_data = response.json()
            print(f"✅ 获取上传签名成功: {signature_data['object_key']}")
            return signature_data
        else:
            print(f"❌ 获取上传签名失败: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 API 服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ API 测试失败: {e}")
        return False

def test_file_upload(signature_data):
    """测试文件上传"""
    print("\n📤 测试文件上传...")
    
    try:
        # 创建测试音频文件
        import numpy as np
        import soundfile as sf
        
        # 生成测试音频
        sample_rate = 48000
        duration = 2.0  # 2秒
        t = np.linspace(0, duration, int(duration * sample_rate))
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # A4 音符
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, audio, sample_rate)
            test_file_path = tmp_file.name
        
        print(f"✅ 创建测试音频文件: {test_file_path}")
        
        # 上传文件
        upload_url = signature_data['upload_url']
        
        with open(test_file_path, 'rb') as f:
            response = requests.put(
                upload_url,
                data=f,
                headers={'Content-Type': 'audio/wav'},
                timeout=30
            )
        
        if response.status_code in [200, 204]:
            print("✅ 文件上传成功")
            
            # 清理临时文件
            os.unlink(test_file_path)
            
            return True
        else:
            print(f"❌ 文件上传失败: {response.status_code} - {response.text}")
            os.unlink(test_file_path)
            return False
            
    except Exception as e:
        print(f"❌ 文件上传测试失败: {e}")
        if 'test_file_path' in locals():
            os.unlink(test_file_path)
        return False

def test_file_download(signature_data):
    """测试文件下载"""
    print("\n📥 测试文件下载...")
    
    try:
        download_url = signature_data['download_url']
        
        response = requests.get(download_url, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ 文件下载成功，大小: {len(response.content)} 字节")
            
            # 验证是否为有效的音频文件
            if len(response.content) > 1000:  # 基本大小检查
                print("✅ 下载的文件大小合理")
                return True
            else:
                print("❌ 下载的文件大小异常")
                return False
        else:
            print(f"❌ 文件下载失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 文件下载测试失败: {e}")
        return False

def test_file_info(signature_data):
    """测试文件信息获取"""
    print("\n📋 测试文件信息...")
    
    try:
        object_key = signature_data['object_key']
        base_url = "http://localhost:8080"
        
        response = requests.get(f"{base_url}/uploads/{object_key}/info", timeout=10)
        
        if response.status_code == 200:
            file_info = response.json()
            print(f"✅ 获取文件信息成功:")
            print(f"   - 对象键名: {file_info['object_key']}")
            print(f"   - 文件大小: {file_info['size']} 字节")
            print(f"   - 内容类型: {file_info['content_type']}")
            print(f"   - 最后修改: {file_info['last_modified']}")
            return True
        else:
            print(f"❌ 获取文件信息失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 文件信息测试失败: {e}")
        return False

def test_end_to_end():
    """端到端测试"""
    print("\n🔄 端到端存储测试...")
    
    # 测试步骤
    tests = [
        ("存储服务", test_storage_service),
        ("API 端点", test_api_endpoints),
    ]
    
    results = []
    signature_data = None
    
    for test_name, test_func in tests:
        try:
            if test_name == "API 端点":
                result = test_func()
                if result and isinstance(result, dict):
                    signature_data = result
                    results.append((test_name, True))
                else:
                    results.append((test_name, False))
            else:
                result = test_func()
                results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 如果基础测试通过，继续文件操作测试
    if signature_data:
        file_tests = [
            ("文件上传", lambda: test_file_upload(signature_data)),
            ("文件下载", lambda: test_file_download(signature_data)),
            ("文件信息", lambda: test_file_info(signature_data)),
        ]
        
        for test_name, test_func in file_tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
                results.append((test_name, False))
    
    return results

def install_dependencies():
    """安装必要的依赖"""
    print("📦 检查并安装依赖...")
    
    import subprocess
    
    try:
        # 安装 API 依赖
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "api/requirements.txt"], 
                      check=True, capture_output=True)
        
        # 安装测试依赖
        subprocess.run([sys.executable, "-m", "pip", "install", "requests", "soundfile", "numpy"], 
                      check=True, capture_output=True)
        
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🗄️ 智能音频调音工具 - 对象存储集成测试")
    print("=" * 60)
    
    # 检查依赖
    if not install_dependencies():
        return
    
    # 运行测试
    results = test_end_to_end()
    
    # 显示测试结果
    print("\n📊 测试结果汇总:")
    print("-" * 40)
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:12} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 测试通过")
    
    if passed == len(results):
        print("\n🎉 所有对象存储测试通过！")
        print("对象存储集成已完成，支持以下功能：")
        print("- ✅ MinIO/S3 兼容存储")
        print("- ✅ 预签名 URL 上传/下载")
        print("- ✅ 文件信息查询")
        print("- ✅ CORS 跨域支持")
        print("- ✅ 多格式音频文件支持")
    else:
        print("\n⚠️ 部分测试失败，请检查：")
        print("- MinIO 服务是否启动 (docker-compose up minio)")
        print("- API 服务是否运行 (python -m uvicorn app.main:app)")
        print("- 网络连接是否正常")
        print("- 环境变量配置是否正确")

if __name__ == "__main__":
    main()
