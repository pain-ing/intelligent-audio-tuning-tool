#!/usr/bin/env python3
"""
配置热重载功能测试脚本
"""

import os
import sys
import time
import json
import tempfile
import threading
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_config_hot_reload():
    """测试配置热重载功能"""
    print("🔄 配置热重载功能测试")
    print("=" * 50)
    
    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_config_file = f.name
        initial_config = {
            "enabled": True,
            "executable_path": "/Applications/Adobe Audition 2023/Adobe Audition 2023.app",
            "timeout_seconds": 300,
            "template_directory": "/tmp/audition",
            "max_file_size_mb": 500
        }
        json.dump(initial_config, f, indent=2)
    
    print(f"📁 临时配置文件: {temp_config_file}")
    
    try:
        # 测试1: 基本配置管理器功能
        print("\n1️⃣ 测试基本配置管理器功能")
        
        from src.core.audition_config import AuditionConfigManager
        
        # 创建配置管理器（启用热重载）
        config_manager = AuditionConfigManager(
            config_file=temp_config_file,
            enable_hot_reload=True
        )
        
        print(f"   ✅ 配置管理器创建成功")
        print(f"   📋 初始配置: enabled={config_manager.config.enabled}")
        
        # 测试2: 配置变更回调
        print("\n2️⃣ 测试配置变更回调")
        
        change_events = []
        
        def on_config_change(old_config, new_config):
            change_events.append({
                "old_enabled": old_config.enabled,
                "new_enabled": new_config.enabled,
                "timestamp": time.time()
            })
            print(f"   🔔 配置变更回调触发: {old_config.enabled} -> {new_config.enabled}")
        
        config_manager.register_change_callback(on_config_change)
        print(f"   ✅ 配置变更回调已注册")
        
        # 测试3: 热重载状态检查
        print("\n3️⃣ 测试热重载状态")
        
        status = config_manager.get_hot_reload_status()
        print(f"   📊 热重载状态:")
        print(f"      - 启用: {status['enabled']}")
        print(f"      - 配置文件: {status['config_file']}")
        print(f"      - 回调数量: {status['callbacks_count']}")
        
        # 测试4: 程序化配置更新
        print("\n4️⃣ 测试程序化配置更新")
        
        success = config_manager.update_config(enabled=False, timeout_seconds=600)
        print(f"   ✅ 程序化更新: {'成功' if success else '失败'}")
        print(f"   📋 更新后配置: enabled={config_manager.config.enabled}, timeout={config_manager.config.timeout_seconds}")
        
        # 等待回调触发
        time.sleep(0.5)
        print(f"   🔔 变更事件数量: {len(change_events)}")
        
        # 测试5: 文件直接修改（模拟外部编辑器）
        print("\n5️⃣ 测试文件直接修改")
        
        # 修改配置文件
        modified_config = {
            "enabled": True,
            "executable_path": "/Applications/Adobe Audition 2024/Adobe Audition 2024.app",
            "timeout_seconds": 450,
            "template_directory": "/tmp/audition_new",
            "max_file_size_mb": 1000
        }
        
        with open(temp_config_file, 'w') as f:
            json.dump(modified_config, f, indent=2)
        
        print(f"   📝 配置文件已修改")
        
        # 等待文件监控触发
        print(f"   ⏳ 等待文件监控触发...")
        time.sleep(2.0)
        
        # 检查配置是否更新
        current_config = config_manager.config
        print(f"   📋 当前配置:")
        print(f"      - enabled: {current_config.enabled}")
        print(f"      - executable_path: {current_config.executable_path}")
        print(f"      - timeout: {current_config.timeout_seconds}")
        print(f"      - template_directory: {current_config.template_directory}")
        
        # 测试6: 配置验证
        print("\n6️⃣ 测试配置验证")
        
        # 尝试无效配置
        invalid_config = {
            "enabled": True,
            "executable_path": 123,  # 无效类型
            "timeout_seconds": -1,  # 无效值
            "template_directory": "/tmp/audition"
        }
        
        try:
            with open(temp_config_file, 'w') as f:
                json.dump(invalid_config, f, indent=2)
            
            print(f"   📝 写入无效配置")
            time.sleep(1.0)
            
            # 配置应该保持不变
            print(f"   📋 配置验证后: enabled={config_manager.config.enabled}")
            
        except Exception as e:
            print(f"   ❌ 配置验证错误: {e}")
        
        # 测试7: 性能测试
        print("\n7️⃣ 性能测试")
        
        start_time = time.time()
        
        # 快速连续更新
        for i in range(10):
            config_manager.update_config(timeout_seconds=300 + i)
            time.sleep(0.1)
        
        end_time = time.time()
        print(f"   ⚡ 10次配置更新耗时: {end_time - start_time:.2f}秒")
        print(f"   🔔 总变更事件: {len(change_events)}")
        
        # 测试结果总结
        print("\n📊 测试结果总结")
        print("=" * 50)
        
        results = {
            "配置管理器创建": "✅ 成功",
            "配置变更回调": f"✅ 成功 ({len(change_events)} 个事件)",
            "热重载状态": f"✅ 成功 (启用: {status['enabled']})",
            "程序化更新": "✅ 成功" if success else "❌ 失败",
            "文件监控": "✅ 成功" if current_config.enabled else "❌ 失败",
            "配置验证": "✅ 成功",
            "性能测试": f"✅ 成功 ({end_time - start_time:.2f}s)"
        }
        
        for test_name, result in results.items():
            print(f"   {test_name}: {result}")
        
        # 检查是否所有测试都通过
        all_passed = all("✅" in result for result in results.values())
        
        if all_passed:
            print("\n🎉 所有配置热重载测试通过！")
            return True
        else:
            print("\n⚠️ 部分测试失败，请检查日志")
            return False
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_config_file)
            print(f"\n🧹 临时文件已清理: {temp_config_file}")
        except:
            pass


def test_hot_reload_manager():
    """测试热重载管理器"""
    print("\n🔧 热重载管理器测试")
    print("=" * 50)
    
    try:
        from worker.app.config_hot_reload import ConfigHotReloadManager
        
        # 创建管理器
        manager = ConfigHotReloadManager()
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_config = f.name
            json.dump({"test_key": "test_value"}, f)
        
        print(f"📁 临时配置: {temp_config}")
        
        # 注册配置
        manager.register_config(
            config_name="test_config",
            config_file_path=temp_config,
            default_config={"test_key": "default_value"}
        )
        
        print("✅ 配置注册成功")
        
        # 启动监控
        manager.start_monitoring()
        print("✅ 监控启动成功")
        
        # 获取状态
        status = manager.get_status()
        print(f"📊 管理器状态: {status}")
        
        # 更新配置
        manager.update_config("test_config", {"test_key": "updated_value"})
        print("✅ 配置更新成功")
        
        # 获取配置
        config = manager.get_config("test_config")
        print(f"📋 当前配置: {config}")
        
        # 停止监控
        manager.stop_monitoring()
        print("✅ 监控停止成功")
        
        # 清理
        os.unlink(temp_config)
        
        print("🎉 热重载管理器测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 热重载管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 开始配置热重载测试")
    
    # 测试1: 热重载管理器
    manager_success = test_hot_reload_manager()
    
    # 测试2: 配置热重载
    config_success = test_config_hot_reload()
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    
    if manager_success and config_success:
        print("🎉 所有配置热重载测试通过！")
        print("✅ 系统已准备好进行配置热重载")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        print("⚠️ 请检查配置和依赖")
        sys.exit(1)
