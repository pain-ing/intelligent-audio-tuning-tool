"""
性能测试套件
"""
import pytest
import time
import asyncio
import tempfile
import os
from pathlib import Path
import numpy as np
import soundfile as sf
from unittest.mock import Mock, patch

# 添加项目路径
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.audio_service import AudioService
from src.utils.memory_optimizer import get_memory_usage, MemoryMonitor
from worker.app.cache_optimized import get_optimized_cache


class TestPerformance:
    """性能测试类"""
    
    @pytest.fixture
    def audio_service(self):
        """音频服务测试夹具"""
        return AudioService()
    
    @pytest.fixture
    def sample_audio_file(self):
        """创建测试音频文件"""
        # 创建5秒的测试音频
        sample_rate = 44100
        duration = 5.0
        samples = int(sample_rate * duration)
        
        # 生成正弦波
        t = np.linspace(0, duration, samples, False)
        audio_data = np.sin(2 * np.pi * 440 * t)  # 440Hz正弦波
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            sf.write(f.name, audio_data, sample_rate)
            yield f.name
        
        # 清理
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass
    
    @pytest.fixture
    def large_audio_file(self):
        """创建大型测试音频文件（用于内存测试）"""
        # 创建60秒的测试音频
        sample_rate = 44100
        duration = 60.0
        samples = int(sample_rate * duration)
        
        # 生成复杂音频（多频率混合）
        t = np.linspace(0, duration, samples, False)
        audio_data = (
            0.3 * np.sin(2 * np.pi * 440 * t) +  # 基频
            0.2 * np.sin(2 * np.pi * 880 * t) +  # 倍频
            0.1 * np.sin(2 * np.pi * 1320 * t)   # 三倍频
        )
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            sf.write(f.name, audio_data, sample_rate)
            yield f.name
        
        # 清理
        try:
            os.unlink(f.name)
        except FileNotFoundError:
            pass
    
    def test_audio_analysis_performance(self, audio_service, sample_audio_file):
        """测试音频分析性能"""
        # 记录初始内存
        initial_memory = get_memory_usage()
        start_time = time.time()
        
        # 执行音频分析
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                audio_service.analyze_features(sample_audio_file)
            )
            
            # 验证结果
            assert result is not None
            assert isinstance(result, dict)
            
            # 性能指标
            duration = time.time() - start_time
            final_memory = get_memory_usage()
            memory_used = final_memory.get('process_rss_mb', 0) - initial_memory.get('process_rss_mb', 0)
            
            # 性能断言
            assert duration < 10.0, f"Analysis took too long: {duration:.2f}s"
            assert memory_used < 100.0, f"Memory usage too high: {memory_used:.1f}MB"
            
            print(f"Audio analysis performance:")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Memory used: {memory_used:.1f}MB")
            
        finally:
            loop.close()
    
    def test_memory_monitoring(self):
        """测试内存监控功能"""
        monitor = MemoryMonitor(warning_threshold=50.0, critical_threshold=80.0)
        
        # 启动监控
        monitor.start_monitoring(interval=0.1)
        
        try:
            # 模拟内存使用
            data = []
            for i in range(100):
                # 创建一些数据
                chunk = np.random.random((1000, 1000))
                data.append(chunk)
                time.sleep(0.01)
            
            # 获取统计信息
            stats = monitor.get_stats()
            
            assert stats.rss_mb > 0
            assert stats.percent >= 0
            assert stats.peak_mb >= stats.rss_mb
            
            print(f"Memory monitoring stats:")
            print(f"  RSS: {stats.rss_mb:.1f}MB")
            print(f"  Peak: {stats.peak_mb:.1f}MB")
            print(f"  Percent: {stats.percent:.1f}%")
            
        finally:
            monitor.stop_monitoring()
            # 清理数据
            del data
    
    def test_cache_performance(self):
        """测试缓存性能"""
        cache = get_optimized_cache()
        cache.clear()  # 清空缓存
        
        # 测试数据
        test_data = {
            f"key_{i}": np.random.random((100, 100)) for i in range(100)
        }
        
        # 测试写入性能
        start_time = time.time()
        for key, value in test_data.items():
            cache.set(key, value)
        write_duration = time.time() - start_time
        
        # 测试读取性能
        start_time = time.time()
        for key in test_data.keys():
            result = cache.get(key)
            assert result is not None
        read_duration = time.time() - start_time
        
        # 获取缓存统计
        stats = cache.get_stats()
        
        # 性能断言
        assert write_duration < 5.0, f"Cache write too slow: {write_duration:.2f}s"
        assert read_duration < 1.0, f"Cache read too slow: {read_duration:.2f}s"
        assert stats['hit_rate'] > 0.9, f"Cache hit rate too low: {stats['hit_rate']:.2f}"
        
        print(f"Cache performance:")
        print(f"  Write duration: {write_duration:.3f}s")
        print(f"  Read duration: {read_duration:.3f}s")
        print(f"  Hit rate: {stats['hit_rate']:.2f}")
        print(f"  Memory usage: {stats['memory_usage_mb']:.1f}MB")
    
    def test_large_file_handling(self, audio_service, large_audio_file):
        """测试大文件处理性能"""
        # 记录初始内存
        initial_memory = get_memory_usage()
        start_time = time.time()
        
        # 执行大文件分析
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                audio_service.analyze_features(large_audio_file)
            )
            
            # 验证结果
            assert result is not None
            assert isinstance(result, dict)
            
            # 性能指标
            duration = time.time() - start_time
            final_memory = get_memory_usage()
            memory_used = final_memory.get('process_rss_mb', 0) - initial_memory.get('process_rss_mb', 0)
            
            # 大文件性能断言（更宽松的限制）
            assert duration < 60.0, f"Large file analysis took too long: {duration:.2f}s"
            assert memory_used < 500.0, f"Memory usage too high for large file: {memory_used:.1f}MB"
            
            print(f"Large file analysis performance:")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Memory used: {memory_used:.1f}MB")
            print(f"  File size: {os.path.getsize(large_audio_file) / (1024*1024):.1f}MB")
            
        finally:
            loop.close()
    
    def test_concurrent_processing(self, audio_service, sample_audio_file):
        """测试并发处理性能"""
        import concurrent.futures
        
        # 记录初始内存
        initial_memory = get_memory_usage()
        start_time = time.time()
        
        # 并发执行多个分析任务
        async def analyze_task():
            return await audio_service.analyze_features(sample_audio_file)
        
        async def run_concurrent_tasks():
            tasks = [analyze_task() for _ in range(5)]
            results = await asyncio.gather(*tasks)
            return results
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(run_concurrent_tasks())
            
            # 验证结果
            assert len(results) == 5
            for result in results:
                assert result is not None
                assert isinstance(result, dict)
            
            # 性能指标
            duration = time.time() - start_time
            final_memory = get_memory_usage()
            memory_used = final_memory.get('process_rss_mb', 0) - initial_memory.get('process_rss_mb', 0)
            
            # 并发性能断言
            assert duration < 30.0, f"Concurrent processing took too long: {duration:.2f}s"
            assert memory_used < 300.0, f"Memory usage too high for concurrent processing: {memory_used:.1f}MB"
            
            print(f"Concurrent processing performance:")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Memory used: {memory_used:.1f}MB")
            print(f"  Tasks completed: {len(results)}")
            
        finally:
            loop.close()


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s"])
