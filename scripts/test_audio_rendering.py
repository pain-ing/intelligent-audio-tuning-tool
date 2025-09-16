#!/usr/bin/env python3
"""
测试音频渲染功能
"""

import os
import sys
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.app.audio_rendering import create_audio_renderer


def create_test_audio(duration=2.0, sample_rate=48000):
    """创建测试音频文件"""
    # 生成简单的正弦波测试音频
    t = np.linspace(0, duration, int(duration * sample_rate), False)
    # 440Hz + 880Hz 的混合音调
    audio = 0.5 * (np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 880 * t))
    
    # 添加一些立体声效果
    stereo_audio = np.column_stack([audio, audio * 0.8])
    
    return stereo_audio, sample_rate


def test_default_renderer():
    """测试默认渲染器"""
    print("测试默认渲染器...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试音频
        audio_data, sample_rate = create_test_audio()
        input_path = os.path.join(temp_dir, "test_input.wav")
        output_path = os.path.join(temp_dir, "test_output.wav")
        
        # 保存测试音频
        sf.write(input_path, audio_data, sample_rate)
        
        # 创建默认渲染器
        renderer = create_audio_renderer(renderer_type="default")
        
        # 测试参数
        style_params = {
            "eq": {
                "bands": [
                    {"freq": 1000, "gain": 3.0, "q": 1.0, "type": "peak"}
                ]
            },
            "compression": {
                "threshold": -20,
                "ratio": 4.0,
                "attack": 5,
                "release": 50
            }
        }
        
        # 执行渲染
        try:
            metrics = renderer.render_audio(input_path, output_path, style_params)
            
            # 检查输出文件
            assert os.path.exists(output_path), "输出文件未生成"
            
            # 检查指标
            assert isinstance(metrics, dict), "指标类型错误"
            
            # 检查输出音频
            output_audio, output_sr = sf.read(output_path)
            assert output_audio.shape[0] > 0, "输出音频为空"
            assert output_sr == sample_rate, "采样率不匹配"
            
            print(f"  ✓ 默认渲染器测试通过")
            print(f"    输入文件大小: {os.path.getsize(input_path)} 字节")
            print(f"    输出文件大小: {os.path.getsize(output_path)} 字节")
            print(f"    处理指标: {list(metrics.keys())}")
            
            return True
            
        except Exception as e:
            print(f"  ✗ 默认渲染器测试失败: {e}")
            return False


def test_audition_renderer():
    """测试Adobe Audition渲染器"""
    print("测试Adobe Audition渲染器...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试音频
        audio_data, sample_rate = create_test_audio()
        input_path = os.path.join(temp_dir, "test_input.wav")
        output_path = os.path.join(temp_dir, "test_output.wav")
        
        # 保存测试音频
        sf.write(input_path, audio_data, sample_rate)
        
        # 创建Adobe Audition渲染器
        renderer = create_audio_renderer(renderer_type="audition")
        
        # 测试参数
        style_params = {
            "eq": {
                "bands": [
                    {"freq": 1000, "gain": 3.0, "q": 1.0, "type": "peak"}
                ]
            },
            "compression": {
                "threshold": -20,
                "ratio": 4.0
            }
        }
        
        # 执行渲染
        try:
            metrics = renderer.render_audio(input_path, output_path, style_params)
            
            # 检查输出文件
            assert os.path.exists(output_path), "输出文件未生成"
            
            # 检查指标
            assert isinstance(metrics, dict), "指标类型错误"
            
            print(f"  ✓ Adobe Audition渲染器测试通过")
            print(f"    渲染器类型: {renderer.renderer_type}")
            print(f"    处理指标: {list(metrics.keys())}")
            
            if hasattr(renderer, 'audition_renderer') and renderer.audition_renderer:
                print("    使用了Adobe Audition渲染")
            else:
                print("    回退到默认渲染器")
            
            return True
            
        except Exception as e:
            print(f"  ✗ Adobe Audition渲染器测试失败: {e}")
            return False


def test_renderer_comparison():
    """测试渲染器对比"""
    print("测试渲染器对比...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试音频
        audio_data, sample_rate = create_test_audio()
        input_path = os.path.join(temp_dir, "test_input.wav")
        
        # 保存测试音频
        sf.write(input_path, audio_data, sample_rate)
        
        # 测试参数
        style_params = {
            "eq": {
                "bands": [
                    {"freq": 1000, "gain": 2.0, "q": 1.0, "type": "peak"}
                ]
            }
        }
        
        results = {}
        
        # 测试不同渲染器
        for renderer_type in ["default", "audition"]:
            output_path = os.path.join(temp_dir, f"output_{renderer_type}.wav")
            
            try:
                renderer = create_audio_renderer(renderer_type=renderer_type)
                metrics = renderer.render_audio(input_path, output_path, style_params)
                
                results[renderer_type] = {
                    "success": True,
                    "metrics": metrics,
                    "file_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0,
                    "actual_type": renderer.renderer_type
                }
                
            except Exception as e:
                results[renderer_type] = {
                    "success": False,
                    "error": str(e)
                }
        
        # 显示对比结果
        print("  渲染器对比结果:")
        for renderer_type, result in results.items():
            if result["success"]:
                print(f"    {renderer_type}: ✓ 成功 (实际类型: {result['actual_type']})")
                print(f"      文件大小: {result['file_size']} 字节")
            else:
                print(f"    {renderer_type}: ✗ 失败 - {result['error']}")
        
        return all(r["success"] for r in results.values())


def main():
    """运行音频渲染测试"""
    print("开始音频渲染功能测试")
    print("=" * 50)
    
    tests = [
        ("默认渲染器", test_default_renderer),
        ("Adobe Audition渲染器", test_audition_renderer),
        ("渲染器对比", test_renderer_comparison)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} - 通过")
            else:
                failed += 1
                print(f"✗ {test_name} - 失败")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} - 异常: {e}")
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有音频渲染测试都通过了！")
        return 0
    else:
        print("⚠️ 部分音频渲染测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
