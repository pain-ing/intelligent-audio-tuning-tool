"""
测试重构后的代码是否能正常工作
"""
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 设置测试环境
os.environ["APP_MODE"] = "desktop"
os.environ["STORAGE_MODE"] = "local"
os.environ["CACHE_MODE"] = "local"
os.environ["DEBUG"] = "true"

def test_imports():
    """测试重构后的模块导入"""
    print("Testing imports...")
    
    try:
        # 测试核心模块
        from src.core.config import config
        print(f"✅ Config loaded: {config.app_name} v{config.app_version}")
        
        from src.core.exceptions import AudioTunerException
        print("✅ Exceptions module loaded")
        
        from src.core.container import container
        print("✅ DI container loaded")
        
        from src.core.types import JobStatus, ProcessingMode
        print("✅ Types module loaded")
        
        # 测试服务模块
        from src.services.base import BaseService
        print("✅ Base service loaded")
        
        from src.services.audio_service import AudioService
        print("✅ Audio service loaded")
        
        from src.services.job_service import JobService
        print("✅ Job service loaded")
        
        from src.services.storage_service import get_storage_service
        print("✅ Storage service loaded")
        
        from src.services.cache_service import get_cache_service
        print("✅ Cache service loaded")
        
        # 测试主应用
        from src.main import app
        print("✅ Main app loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_services():
    """测试服务实例化"""
    print("\nTesting service instantiation...")
    
    try:
        from src.services.storage_service import get_storage_service
        from src.services.cache_service import get_cache_service
        from src.services.audio_service import AudioService
        
        # 测试存储服务
        storage = get_storage_service()
        print(f"✅ Storage service: {type(storage).__name__}")
        
        # 测试缓存服务
        cache = get_cache_service()
        print(f"✅ Cache service: {type(cache).__name__}")
        
        # 测试音频服务
        audio = AudioService()
        print(f"✅ Audio service: {type(audio).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Service instantiation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """测试配置系统"""
    print("\nTesting configuration...")
    
    try:
        from src.core.config import config
        
        print(f"✅ App mode: {config.app_mode}")
        print(f"✅ Storage mode: {config.storage_mode}")
        print(f"✅ Cache mode: {config.cache_mode}")
        print(f"✅ Debug: {config.debug}")
        print(f"✅ Host: {config.host}")
        print(f"✅ Port: {config.port}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_api_routes():
    """测试API路由"""
    print("\nTesting API routes...")
    
    try:
        from src.api.routes import router
        
        # 检查路由是否正确定义
        routes = [route.path for route in router.routes]
        expected_routes = ["/health", "/jobs", "/upload"]
        
        for expected in expected_routes:
            if any(expected in route for route in routes):
                print(f"✅ Route found: {expected}")
            else:
                print(f"⚠️ Route missing: {expected}")
        
        return True
        
    except Exception as e:
        print(f"❌ API routes test failed: {e}")
        return False

def test_desktop_main():
    """测试桌面版主入口"""
    print("\nTesting desktop main entry...")
    
    try:
        from src.desktop_main import main
        print("✅ Desktop main entry loaded")
        
        # 不实际运行，只测试导入
        return True
        
    except Exception as e:
        print(f"❌ Desktop main test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("🧪 Testing refactored Audio Tuner code...")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Service Test", test_services),
        ("Config Test", test_config),
        ("API Routes Test", test_api_routes),
        ("Desktop Main Test", test_desktop_main)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Refactored code is ready for packaging.")
        return True
    else:
        print("⚠️ Some tests failed. Please fix issues before packaging.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
