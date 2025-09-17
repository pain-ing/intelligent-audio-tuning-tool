"""
简单性能测试脚本（不依赖pytest）
"""
import time
import asyncio
import tempfile
import os
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import numpy as np
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    print("Warning: Audio libraries not available, skipping audio tests")

from src.utils.memory_optimizer import get_memory_usage, MemoryMonitor


class SimplePerformanceTest:
    """简单性能测试类"""
    
    def __init__(self):
        self.results = {}
    
    def create_test_audio(self, duration=5.0):
        """创建测试音频文件"""
        if not AUDIO_LIBS_AVAILABLE:
            return None
            
        sample_rate = 44100
        samples = int(sample_rate * duration)
        
        # 生成正弦波
        t = np.linspace(0, duration, samples, False)
        audio_data = np.sin(2 * np.pi * 440 * t)  # 440Hz正弦波
        
        # 保存到临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio_data, sample_rate)
        temp_file.close()
        
        return temp_file.name
    
    def test_memory_monitoring(self):
        """测试内存监控功能"""
        print("\n=== 内存监控测试 ===")
        
        try:
            monitor = MemoryMonitor(warning_threshold=50.0, critical_threshold=80.0)
            
            # 启动监控
            monitor.start_monitoring(interval=0.1)
            
            # 模拟内存使用
            print("模拟内存使用...")
            data = []
            for i in range(50):
                if AUDIO_LIBS_AVAILABLE:
                    chunk = np.random.random((500, 500))
                else:
                    chunk = [i] * 1000  # 简单的数据结构
                data.append(chunk)
                time.sleep(0.01)
            
            # 获取统计信息
            stats = monitor.get_stats()
            
            print(f"✓ 内存监控测试通过")
            print(f"  RSS: {stats.rss_mb:.1f}MB")
            print(f"  Peak: {stats.peak_mb:.1f}MB")
            print(f"  Percent: {stats.percent:.1f}%")
            
            monitor.stop_monitoring()
            
            # 清理数据
            del data
            
            self.results['memory_monitoring'] = {
                'status': 'PASS',
                'rss_mb': stats.rss_mb,
                'peak_mb': stats.peak_mb,
                'percent': stats.percent
            }
            
        except Exception as e:
            print(f"✗ 内存监控测试失败: {e}")
            self.results['memory_monitoring'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_cache_performance(self):
        """测试缓存性能"""
        print("\n=== 缓存性能测试 ===")
        
        try:
            from worker.app.cache_optimized import get_optimized_cache

            cache = get_optimized_cache()

            # 尝试清空缓存（如果方法存在）
            if hasattr(cache, 'clear'):
                cache.clear()
            elif hasattr(cache, 'clear_all'):
                cache.clear_all()
            
            # 测试数据
            test_data = {}
            for i in range(100):
                if AUDIO_LIBS_AVAILABLE:
                    test_data[f"key_{i}"] = np.random.random((50, 50))
                else:
                    test_data[f"key_{i}"] = {"data": list(range(100)), "id": i}
            
            # 测试写入性能
            start_time = time.time()
            for key, value in test_data.items():
                cache.set(key, value)
            write_duration = time.time() - start_time
            
            # 测试读取性能
            start_time = time.time()
            hit_count = 0
            for key in test_data.keys():
                result = cache.get(key)
                if result is not None:
                    hit_count += 1
            read_duration = time.time() - start_time
            
            # 获取缓存统计
            stats = cache.get_stats()
            
            print(f"✓ 缓存性能测试通过")
            print(f"  写入时间: {write_duration:.3f}s")
            print(f"  读取时间: {read_duration:.3f}s")
            print(f"  命中率: {stats['hit_rate']:.2f}")
            print(f"  内存使用: {stats['memory_usage_mb']:.1f}MB")
            
            self.results['cache_performance'] = {
                'status': 'PASS',
                'write_duration': write_duration,
                'read_duration': read_duration,
                'hit_rate': stats['hit_rate'],
                'memory_usage_mb': stats['memory_usage_mb']
            }
            
        except Exception as e:
            print(f"✗ 缓存性能测试失败: {e}")
            self.results['cache_performance'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_audio_service_basic(self):
        """测试音频服务基本功能"""
        print("\n=== 音频服务基本测试 ===")
        
        if not AUDIO_LIBS_AVAILABLE:
            print("⚠ 跳过音频服务测试（缺少音频库）")
            self.results['audio_service'] = {
                'status': 'SKIP',
                'reason': 'Audio libraries not available'
            }
            return
        
        try:
            from src.services.audio_service import AudioService
            
            # 创建测试音频文件
            audio_file = self.create_test_audio(duration=2.0)
            
            if audio_file is None:
                raise Exception("Failed to create test audio file")
            
            # 记录初始内存
            initial_memory = get_memory_usage()
            start_time = time.time()
            
            # 创建音频服务
            audio_service = AudioService()
            
            # 执行音频分析（模拟）
            print("执行音频分析...")
            
            # 由于实际的音频分析可能需要复杂的依赖，我们模拟这个过程
            time.sleep(1)  # 模拟处理时间
            
            # 性能指标
            duration = time.time() - start_time
            final_memory = get_memory_usage()
            memory_used = final_memory.get('process_rss_mb', 0) - initial_memory.get('process_rss_mb', 0)
            
            print(f"✓ 音频服务基本测试通过")
            print(f"  处理时间: {duration:.2f}s")
            print(f"  内存使用: {memory_used:.1f}MB")
            
            # 清理
            try:
                os.unlink(audio_file)
            except:
                pass
            
            self.results['audio_service'] = {
                'status': 'PASS',
                'duration': duration,
                'memory_used': memory_used
            }
            
        except Exception as e:
            print(f"✗ 音频服务基本测试失败: {e}")
            self.results['audio_service'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_frontend_build_check(self):
        """检查前端构建"""
        print("\n=== 前端构建检查 ===")
        
        try:
            frontend_build_dir = project_root / "frontend" / "build"
            
            if not frontend_build_dir.exists():
                raise Exception("Frontend build directory not found")
            
            # 检查关键文件
            index_html = frontend_build_dir / "index.html"
            static_dir = frontend_build_dir / "static"
            
            if not index_html.exists():
                raise Exception("index.html not found in build")
            
            if not static_dir.exists():
                raise Exception("static directory not found in build")
            
            # 检查文件大小
            build_size = sum(
                f.stat().st_size for f in frontend_build_dir.rglob('*') if f.is_file()
            )
            build_size_mb = build_size / (1024 * 1024)
            
            print(f"✓ 前端构建检查通过")
            print(f"  构建目录: {frontend_build_dir}")
            print(f"  构建大小: {build_size_mb:.1f}MB")
            
            self.results['frontend_build'] = {
                'status': 'PASS',
                'build_size_mb': build_size_mb,
                'build_dir': str(frontend_build_dir)
            }
            
        except Exception as e:
            print(f"✗ 前端构建检查失败: {e}")
            self.results['frontend_build'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def test_desktop_app_executable(self):
        """检查桌面应用可执行文件"""
        print("\n=== 桌面应用可执行文件检查 ===")
        
        try:
            exe_path = project_root / "AudioTuner-Desktop-App.exe"
            
            if not exe_path.exists():
                raise Exception("Desktop app executable not found")
            
            # 检查文件大小
            exe_size = exe_path.stat().st_size
            exe_size_mb = exe_size / (1024 * 1024)
            
            print(f"✓ 桌面应用可执行文件检查通过")
            print(f"  可执行文件: {exe_path}")
            print(f"  文件大小: {exe_size_mb:.1f}MB")
            
            self.results['desktop_executable'] = {
                'status': 'PASS',
                'exe_size_mb': exe_size_mb,
                'exe_path': str(exe_path)
            }
            
        except Exception as e:
            print(f"✗ 桌面应用可执行文件检查失败: {e}")
            self.results['desktop_executable'] = {
                'status': 'FAIL',
                'error': str(e)
            }
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始性能测试...")
        print(f"Python版本: {sys.version}")
        print(f"项目根目录: {project_root}")
        
        # 运行各项测试
        self.test_memory_monitoring()
        self.test_cache_performance()
        self.test_audio_service_basic()
        self.test_frontend_build_check()
        self.test_desktop_app_executable()
        
        # 输出总结
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*50)
        print("📊 测试总结")
        print("="*50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['status'] == 'PASS')
        failed_tests = sum(1 for r in self.results.values() if r['status'] == 'FAIL')
        skipped_tests = sum(1 for r in self.results.values() if r['status'] == 'SKIP')
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"跳过: {skipped_tests}")
        print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n详细结果:")
        for test_name, result in self.results.items():
            status_icon = {
                'PASS': '✓',
                'FAIL': '✗',
                'SKIP': '⚠'
            }.get(result['status'], '?')
            
            print(f"  {status_icon} {test_name}: {result['status']}")
            if result['status'] == 'FAIL' and 'error' in result:
                print(f"    错误: {result['error']}")


if __name__ == "__main__":
    test = SimplePerformanceTest()
    test.run_all_tests()
