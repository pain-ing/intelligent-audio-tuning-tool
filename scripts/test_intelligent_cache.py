#!/usr/bin/env python3
"""
智能缓存系统测试脚本
"""

import os
import sys
import tempfile
import shutil
import time
import json
import numpy as np
import soundfile as sf
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_audio_file(file_path: str, duration: float = 1.0, 
                          sample_rate: int = 44100, frequency: float = 440):
    """创建测试音频文件"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * frequency * t)
    sf.write(file_path, audio_data, sample_rate)
    return file_path


def test_cache_basic_operations():
    """测试缓存基本操作"""
    print("🗄️ 测试缓存基本操作")
    print("-" * 40)
    
    try:
        from worker.app.intelligent_cache import IntelligentCache, CacheType
        
        # 创建临时缓存目录
        temp_cache_dir = tempfile.mkdtemp(prefix="cache_test_")
        cache = IntelligentCache(cache_dir=temp_cache_dir, max_size_mb=10)
        print("✅ 缓存系统创建成功")
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        
        try:
            input_file = os.path.join(temp_dir, "input.wav")
            output_file = os.path.join(temp_dir, "output.wav")
            
            create_test_audio_file(input_file, duration=0.5)
            create_test_audio_file(output_file, duration=0.5, frequency=880)
            
            # 测试存储缓存
            params = {"effect": "reverb", "intensity": 0.5}
            success = cache.put(
                input_file, params, CacheType.AUDIO_PROCESSING, 
                output_file, {"test": "data"}
            )
            assert success, "缓存存储失败"
            print("✅ 缓存存储成功")
            
            # 测试获取缓存
            cached_file = cache.get(input_file, params, CacheType.AUDIO_PROCESSING)
            assert cached_file is not None, "缓存获取失败"
            assert os.path.exists(cached_file), "缓存文件不存在"
            print("✅ 缓存获取成功")
            
            # 测试缓存未命中（不同参数）
            different_params = {"effect": "reverb", "intensity": 0.8}
            cached_file_2 = cache.get(input_file, different_params, CacheType.AUDIO_PROCESSING)
            assert cached_file_2 is None, "应该缓存未命中"
            print("✅ 缓存未命中测试通过")
            
            # 测试统计信息
            stats = cache.get_stats()
            assert stats.total_entries > 0, "统计信息错误"
            assert stats.hit_count > 0, "命中次数错误"
            assert stats.miss_count > 0, "未命中次数错误"
            print(f"✅ 统计信息: 条目数={stats.total_entries}, 命中率={stats.hit_rate:.2f}")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(temp_cache_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 缓存基本操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_expiration():
    """测试缓存过期"""
    print("\n⏰ 测试缓存过期")
    print("-" * 40)
    
    try:
        from worker.app.intelligent_cache import IntelligentCache, CacheType
        
        # 创建临时缓存目录
        temp_cache_dir = tempfile.mkdtemp(prefix="expire_test_")
        cache = IntelligentCache(cache_dir=temp_cache_dir, default_ttl=1.0)  # 1秒过期
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        
        try:
            input_file = os.path.join(temp_dir, "input.wav")
            output_file = os.path.join(temp_dir, "output.wav")
            
            create_test_audio_file(input_file)
            create_test_audio_file(output_file, frequency=880)
            
            # 存储缓存
            params = {"test": "expiration"}
            success = cache.put(
                input_file, params, CacheType.AUDIO_PROCESSING, 
                output_file, ttl=1.0
            )
            assert success, "缓存存储失败"
            print("✅ 短期缓存存储成功")
            
            # 立即获取应该成功
            cached_file = cache.get(input_file, params, CacheType.AUDIO_PROCESSING)
            assert cached_file is not None, "立即获取缓存失败"
            print("✅ 立即获取缓存成功")
            
            # 等待过期
            print("⏳ 等待缓存过期...")
            time.sleep(1.5)
            
            # 过期后获取应该失败
            cached_file_expired = cache.get(input_file, params, CacheType.AUDIO_PROCESSING)
            assert cached_file_expired is None, "过期缓存应该返回None"
            print("✅ 过期缓存清理成功")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(temp_cache_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 缓存过期测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_manager():
    """测试缓存管理器"""
    print("\n🎛️ 测试缓存管理器")
    print("-" * 40)
    
    try:
        from worker.app.intelligent_cache import IntelligentCache, CacheManager, CacheType
        
        # 创建临时缓存目录
        temp_cache_dir = tempfile.mkdtemp(prefix="manager_test_")
        cache = IntelligentCache(cache_dir=temp_cache_dir)
        manager = CacheManager(cache)
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        
        try:
            input_file = os.path.join(temp_dir, "input.wav")
            create_test_audio_file(input_file)
            
            # 定义处理函数
            def test_processor(input_path, output_path, params):
                # 简单的处理：复制文件并添加一些修改
                create_test_audio_file(output_path, frequency=params.get("frequency", 880))
                return True
            
            # 第一次处理（缓存未命中）
            params = {"frequency": 880, "effect": "test"}
            result_file, from_cache = manager.get_or_process_audio(
                input_file, params, test_processor, CacheType.AUDIO_PROCESSING
            )
            
            assert os.path.exists(result_file), "处理结果文件不存在"
            assert not from_cache, "第一次应该不是来自缓存"
            print("✅ 第一次处理成功（缓存未命中）")
            
            # 第二次处理（缓存命中）
            result_file_2, from_cache_2 = manager.get_or_process_audio(
                input_file, params, test_processor, CacheType.AUDIO_PROCESSING
            )
            
            assert os.path.exists(result_file_2), "缓存结果文件不存在"
            assert from_cache_2, "第二次应该来自缓存"
            print("✅ 第二次处理成功（缓存命中）")
            
            # 测试缓存失效
            manager.invalidate_cache(input_file, params, CacheType.AUDIO_PROCESSING)
            print("✅ 缓存失效成功")
            
            # 失效后再次处理
            result_file_3, from_cache_3 = manager.get_or_process_audio(
                input_file, params, test_processor, CacheType.AUDIO_PROCESSING
            )
            
            assert not from_cache_3, "失效后应该不是来自缓存"
            print("✅ 失效后重新处理成功")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(temp_cache_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 缓存管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_cleanup():
    """测试缓存清理"""
    print("\n🧹 测试缓存清理")
    print("-" * 40)
    
    try:
        from worker.app.intelligent_cache import IntelligentCache, CacheType
        
        # 创建小容量缓存
        temp_cache_dir = tempfile.mkdtemp(prefix="cleanup_test_")
        cache = IntelligentCache(
            cache_dir=temp_cache_dir, 
            max_size_mb=1,  # 1MB限制
            max_entries=3   # 最多3个条目
        )
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        
        try:
            # 创建多个缓存条目
            for i in range(5):
                input_file = os.path.join(temp_dir, f"input_{i}.wav")
                output_file = os.path.join(temp_dir, f"output_{i}.wav")
                
                create_test_audio_file(input_file, duration=0.2)
                create_test_audio_file(output_file, duration=0.2, frequency=440 + i * 100)
                
                params = {"index": i, "frequency": 440 + i * 100}
                success = cache.put(
                    input_file, params, CacheType.AUDIO_PROCESSING, output_file
                )
                
                if success:
                    print(f"✅ 缓存条目 {i} 存储成功")
                else:
                    print(f"⚠️ 缓存条目 {i} 存储失败（可能触发清理）")
                
                # 短暂延迟以确保时间戳不同
                time.sleep(0.1)
            
            # 检查最终状态
            stats = cache.get_stats()
            print(f"✅ 最终缓存状态: 条目数={stats.total_entries}, 大小={stats.total_size}字节")
            
            # 验证条目数限制
            assert stats.total_entries <= 3, f"条目数超过限制: {stats.total_entries}"
            print("✅ 条目数限制验证通过")
            
            # 测试手动清理
            deleted_count = cache.clear_cache(CacheType.AUDIO_PROCESSING)
            print(f"✅ 手动清理完成，删除 {deleted_count} 个条目")
            
            # 验证清理结果
            stats_after = cache.get_stats()
            assert stats_after.total_entries == 0, "清理后应该没有条目"
            print("✅ 清理验证通过")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(temp_cache_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 缓存清理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_types():
    """测试不同缓存类型"""
    print("\n📂 测试不同缓存类型")
    print("-" * 40)
    
    try:
        from worker.app.intelligent_cache import IntelligentCache, CacheType
        
        # 创建临时缓存目录
        temp_cache_dir = tempfile.mkdtemp(prefix="types_test_")
        cache = IntelligentCache(cache_dir=temp_cache_dir)
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        
        try:
            input_file = os.path.join(temp_dir, "input.wav")
            create_test_audio_file(input_file)
            
            # 测试不同类型的缓存
            cache_types = [
                CacheType.AUDIO_PROCESSING,
                CacheType.FORMAT_CONVERSION,
                CacheType.QUALITY_ANALYSIS,
                CacheType.BATCH_PROCESSING,
                CacheType.AUDITION_RENDERING
            ]
            
            for cache_type in cache_types:
                output_file = os.path.join(temp_dir, f"output_{cache_type.value}.wav")
                create_test_audio_file(output_file, frequency=440 + len(cache_type.value) * 10)
                
                params = {"type": cache_type.value, "test": True}
                
                # 存储缓存
                success = cache.put(input_file, params, cache_type, output_file)
                assert success, f"缓存类型 {cache_type.value} 存储失败"
                
                # 获取缓存
                cached_file = cache.get(input_file, params, cache_type)
                assert cached_file is not None, f"缓存类型 {cache_type.value} 获取失败"
                
                print(f"✅ 缓存类型 {cache_type.value} 测试通过")
            
            # 验证不同类型之间的隔离
            params_1 = {"test": "isolation"}
            output_1 = os.path.join(temp_dir, "isolation_1.wav")
            output_2 = os.path.join(temp_dir, "isolation_2.wav")
            
            create_test_audio_file(output_1, frequency=1000)
            create_test_audio_file(output_2, frequency=2000)
            
            # 相同参数，不同类型
            cache.put(input_file, params_1, CacheType.AUDIO_PROCESSING, output_1)
            cache.put(input_file, params_1, CacheType.FORMAT_CONVERSION, output_2)
            
            cached_1 = cache.get(input_file, params_1, CacheType.AUDIO_PROCESSING)
            cached_2 = cache.get(input_file, params_1, CacheType.FORMAT_CONVERSION)
            
            assert cached_1 != cached_2, "不同类型的缓存应该是独立的"
            print("✅ 缓存类型隔离验证通过")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(temp_cache_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 缓存类型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_info():
    """测试缓存信息获取"""
    print("\n📊 测试缓存信息获取")
    print("-" * 40)
    
    try:
        from worker.app.intelligent_cache import IntelligentCache, CacheType
        
        # 创建临时缓存目录
        temp_cache_dir = tempfile.mkdtemp(prefix="info_test_")
        cache = IntelligentCache(cache_dir=temp_cache_dir)
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="audio_test_")
        
        try:
            # 添加一些缓存条目
            for i in range(3):
                input_file = os.path.join(temp_dir, f"input_{i}.wav")
                output_file = os.path.join(temp_dir, f"output_{i}.wav")
                
                create_test_audio_file(input_file, duration=0.3)
                create_test_audio_file(output_file, duration=0.3, frequency=440 + i * 200)
                
                params = {"index": i}
                cache.put(input_file, params, CacheType.AUDIO_PROCESSING, output_file)
                
                # 访问一次以更新统计
                cache.get(input_file, params, CacheType.AUDIO_PROCESSING)
            
            # 获取缓存信息
            cache_info = cache.get_cache_info()
            assert len(cache_info) == 3, f"应该有3个缓存条目，实际: {len(cache_info)}"
            print(f"✅ 缓存信息获取成功，条目数: {len(cache_info)}")
            
            # 检查信息字段
            for info in cache_info:
                required_fields = [
                    "cache_key", "cache_type", "created_at", "last_accessed",
                    "access_count", "file_size", "age", "last_access_age"
                ]
                
                for field in required_fields:
                    assert field in info, f"缺少字段: {field}"
                
                assert info["access_count"] > 0, "访问次数应该大于0"
                assert info["file_size"] > 0, "文件大小应该大于0"
            
            print("✅ 缓存信息字段验证通过")
            
            # 测试按类型过滤
            filtered_info = cache.get_cache_info(CacheType.AUDIO_PROCESSING)
            assert len(filtered_info) == 3, "按类型过滤结果错误"
            print("✅ 按类型过滤验证通过")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            shutil.rmtree(temp_cache_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 缓存信息测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 智能缓存系统测试")
    print("=" * 60)
    
    tests = [
        ("缓存基本操作", test_cache_basic_operations),
        ("缓存过期", test_cache_expiration),
        ("缓存管理器", test_cache_manager),
        ("缓存清理", test_cache_cleanup),
        ("缓存类型", test_cache_types),
        ("缓存信息", test_cache_info)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results[test_name] = False
    
    # 测试结果总结
    print("\n" + "=" * 60)
    print("📋 智能缓存系统测试结果总结")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📊 测试统计: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 智能缓存系统 - 所有测试通过！")
        print("✅ 智能缓存机制功能已准备就绪")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
