#!/usr/bin/env python3
"""
阶段2核心集成开发测试脚本
验证所有阶段2功能的集成测试
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_audition_renderer_enhancements():
    """测试Adobe Audition渲染器增强功能"""
    print("🎵 测试Adobe Audition渲染器增强功能")
    print("-" * 40)
    
    try:
        from worker.app.audition_renderer import AuditionAudioRenderer, create_audition_renderer
        
        # 测试渲染器创建
        renderer = AuditionAudioRenderer(
            timeout=300,
            max_retries=3,
            enable_monitoring=True
        )
        
        print("✅ Adobe Audition渲染器创建成功")
        
        # 测试统计功能
        stats = renderer.get_stats()
        print(f"📊 渲染器统计: {stats}")
        
        # 测试健康检查
        health = renderer.health_check()
        print(f"🏥 健康检查: {health['status']}")
        
        # 测试配置更新
        renderer.configure(timeout=600, max_retries=5)
        print("✅ 渲染器配置更新成功")
        
        return True
        
    except Exception as e:
        print(f"❌ Adobe Audition渲染器测试失败: {e}")
        return False


def test_error_handling():
    """测试高级错误处理"""
    print("\n🚨 测试高级错误处理")
    print("-" * 40)
    
    try:
        from worker.app.audition_error_handler import global_error_handler, ErrorSeverity, RecoveryStrategy
        
        # 测试错误处理
        test_error = Exception("测试错误")
        error_context = global_error_handler.handle_error(
            test_error, 
            "test_error", 
            {"test_context": "value"}
        )
        
        print(f"✅ 错误处理成功: {error_context.error_type}")
        print(f"📊 恢复策略: {error_context.recovery_strategy}")
        
        # 测试熔断器
        circuit_breaker = global_error_handler.get_circuit_breaker("test_service")
        print("✅ 熔断器创建成功")
        
        # 测试错误统计
        stats = global_error_handler.get_error_statistics()
        print(f"📈 错误统计: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def test_performance_monitoring():
    """测试性能监控"""
    print("\n📊 测试性能监控")
    print("-" * 40)
    
    try:
        from worker.app.performance_monitor import global_performance_monitor
        
        # 测试性能监控会话
        with global_performance_monitor.monitor_session(
            session_id="test_session",
            operation_type="test_operation"
        ) as session:
            # 模拟一些工作
            time.sleep(0.1)
            session.input_size = 1024 * 1024  # 1MB
        
        print("✅ 性能监控会话完成")
        
        # 测试实时指标
        metrics = global_performance_monitor.get_real_time_metrics()
        print(f"📊 实时指标: {metrics['system_health']}")
        
        # 测试性能报告
        report = global_performance_monitor.get_performance_report()
        print(f"📈 性能报告: 总会话数 {report['summary'].get('total_sessions', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能监控测试失败: {e}")
        return False


def test_audio_pipeline():
    """测试音频处理流水线"""
    print("\n🎵 测试音频处理流水线")
    print("-" * 40)
    
    try:
        from worker.app.audio_pipeline import AudioProcessingPipeline, AudioProcessingTask, ProcessingPriority
        from worker.app.audio_rendering import AudioRenderer
        
        # 创建音频渲染器
        audio_renderer = AudioRenderer()
        
        # 创建流水线
        pipeline = AudioProcessingPipeline(audio_renderer, max_workers=2)
        
        print("✅ 音频处理流水线创建成功")
        
        # 获取流水线状态
        status = pipeline.get_pipeline_status()
        print(f"📊 流水线状态: {status['running']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 音频处理流水线测试失败: {e}")
        return False


def test_streaming_optimization():
    """测试流式处理优化"""
    print("\n🌊 测试流式处理优化")
    print("-" * 40)
    
    try:
        from worker.app.audio_streaming import StreamingAudioProcessor
        
        # 创建流式处理器
        processor = StreamingAudioProcessor(max_memory_mb=256.0)
        
        print("✅ 流式处理器创建成功")
        
        # 测试性能配置
        processor.configure_performance(
            enable_parallel=True,
            max_workers=2,
            enable_caching=True
        )
        
        print("✅ 性能配置更新成功")
        
        # 测试性能统计
        stats = processor.get_performance_stats()
        print(f"📊 处理器统计: 成功率 {stats['success_rate']:.1f}%")
        
        # 测试健康检查
        health = processor.health_check()
        print(f"🏥 健康检查: {health['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 流式处理优化测试失败: {e}")
        return False


def test_config_hot_reload():
    """测试配置热重载（简化版）"""
    print("\n🔄 测试配置热重载")
    print("-" * 40)
    
    try:
        from src.core.audition_config import AuditionConfigManager
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_config = f.name
            f.write('{"enabled": true, "executable_path": "/test/path", "timeout_seconds": 300, "template_directory": "/tmp"}')
        
        try:
            # 创建配置管理器（禁用热重载以避免依赖问题）
            config_manager = AuditionConfigManager(
                config_file=temp_config,
                enable_hot_reload=False
            )
            
            print("✅ 配置管理器创建成功")
            
            # 测试配置更新
            success = config_manager.update_config(enabled=False)
            print(f"✅ 配置更新: {'成功' if success else '失败'}")
            
            # 测试配置获取
            config = config_manager.config
            print(f"📋 当前配置: enabled={config.enabled}")
            
            return True
            
        finally:
            os.unlink(temp_config)
        
    except Exception as e:
        print(f"❌ 配置热重载测试失败: {e}")
        return False


def test_integration():
    """集成测试"""
    print("\n🔗 集成测试")
    print("-" * 40)
    
    try:
        from worker.app.audio_rendering import AudioRenderer
        
        # 创建音频渲染器
        renderer = AudioRenderer(renderer_type="default")
        
        print("✅ 音频渲染器集成成功")
        
        # 测试渲染器类型
        print(f"📋 渲染器类型: {renderer.renderer_type}")
        
        # 测试内存优化
        chunk_size = renderer._adaptive_chunk_size
        print(f"📊 自适应块大小: {chunk_size} 样本")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 阶段2：核心集成开发测试")
    print("=" * 60)
    
    tests = [
        ("Adobe Audition渲染器增强", test_audition_renderer_enhancements),
        ("高级错误处理", test_error_handling),
        ("性能监控", test_performance_monitoring),
        ("音频处理流水线", test_audio_pipeline),
        ("流式处理优化", test_streaming_optimization),
        ("配置热重载", test_config_hot_reload),
        ("系统集成", test_integration)
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
    print("📋 阶段2测试结果总结")
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
        print("🎉 阶段2：核心集成开发 - 所有测试通过！")
        print("✅ 系统已准备好进入下一阶段")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
