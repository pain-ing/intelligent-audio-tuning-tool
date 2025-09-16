#!/usr/bin/env python3
"""
测试桌面应用程序是否正常工作
"""

import requests
import time
import subprocess
import sys
from pathlib import Path

def test_api_endpoint():
    """测试 API 端点是否正常响应"""
    try:
        response = requests.get("http://127.0.0.1:8080/", timeout=5)
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            # 检查是否返回 HTML 内容（前端）而不是 JSON（API）
            content_type = response.headers.get('content-type', '')
            print(f"Content-Type: {content_type}")
            
            if 'text/html' in content_type:
                print("✅ Frontend is being served correctly!")
                return True
            elif 'application/json' in content_type:
                print("❌ API JSON is being served instead of frontend")
                print("Response:", response.json())
                return False
            else:
                print(f"⚠️  Unexpected content type: {content_type}")
                return False
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to API: {e}")
        return False

def test_static_files():
    """测试静态文件是否可访问"""
    static_urls = [
        "http://127.0.0.1:8080/static/css/",
        "http://127.0.0.1:8080/static/js/",
    ]
    
    for url in static_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 403, 404]:  # 403/404 也表示路径存在
                print(f"✅ Static path accessible: {url}")
            else:
                print(f"❌ Static path issue: {url} -> {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Static path error: {url} -> {e}")

def main():
    print("🧪 Testing AudioTuner Desktop App...")
    print("=" * 50)
    
    # 检查可执行文件是否存在
    exe_path = Path("AudioTuner-Desktop-App.exe")
    if not exe_path.exists():
        print("❌ AudioTuner-Desktop-App.exe not found!")
        print("Please run 'python build_exe.py' first.")
        return False
    
    print(f"✅ Executable found: {exe_path} ({exe_path.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # 测试 API 端点
    print("\n📡 Testing API endpoint...")
    api_ok = test_api_endpoint()
    
    # 测试静态文件
    print("\n📁 Testing static files...")
    test_static_files()
    
    # 总结
    print("\n" + "=" * 50)
    if api_ok:
        print("🎉 Desktop app appears to be working correctly!")
        print("\nTo launch the desktop app:")
        print("1. Double-click: AudioTuner-Desktop-App.exe")
        print("2. Or use desktop shortcut: 'AudioTuner 桌面应用'")
        print("\nThe app should open in a native desktop window.")
    else:
        print("❌ Desktop app has issues. Check the logs above.")
        print("\nTroubleshooting:")
        print("1. Make sure no other instance is running")
        print("2. Check if port 8080 is available")
        print("3. Try rebuilding: python build_exe.py")
    
    return api_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
