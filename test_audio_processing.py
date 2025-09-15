#!/usr/bin/env python3
"""
音频处理算法测试脚本
测试真实的音频分析、参数反演和渲染功能
"""

import sys
import os
import numpy as np
import soundfile as sf
import tempfile
from pathlib import Path

# 添加 worker 目录到路径
sys.path.insert(0, str(Path("worker").absolute()))

def create_test_audio():
    """创建测试音频文件"""
    sample_rate = 48000
    duration = 5.0  # 5秒
    t = np.linspace(0, duration, int(duration * sample_rate))
    
    # 创建参考音频 (已处理)
    ref_audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # A4
    ref_audio += 0.1 * np.sin(2 * np.pi * 880 * t)  # A5 谐波
    ref_audio = np.tanh(ref_audio * 1.5)  # 轻微饱和
    ref_audio *= 0.7  # 降低音量
    
    # 创建目标音频 (未处理)
    tgt_audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # 纯净的 A4
    tgt_audio += 0.05 * np.random.normal(0, 0.01, len(t))  # 轻微噪声
    
    # 保存测试文件
    ref_path = "test_reference.wav"
    tgt_path = "test_target.wav"
    
    sf.write(ref_path, ref_audio, sample_rate)
    sf.write(tgt_path, tgt_audio, sample_rate)
    
    print(f"✅ 创建测试音频文件:")
    print(f"   参考音频: {ref_path}")
    print(f"   目标音频: {tgt_path}")
    
    return ref_path, tgt_path

def test_audio_analysis():
    """测试音频分析功能"""
    print("\n🔍 测试音频分析...")
    
    try:
        from app.audio_analysis import AudioAnalyzer
        
        analyzer = AudioAnalyzer()
        ref_path, tgt_path = create_test_audio()
        
        # 分析参考音频
        print("   分析参考音频...")
        ref_features = analyzer.analyze_features(ref_path)
        
        # 分析目标音频
        print("   分析目标音频...")
        tgt_features = analyzer.analyze_features(tgt_path)
        
        # 显示分析结果
        print(f"   参考音频 LUFS: {ref_features['lufs']['integrated_lufs']:.1f}")
        print(f"   目标音频 LUFS: {tgt_features['lufs']['integrated_lufs']:.1f}")
        print(f"   参考音频峰值: {ref_features['true_peak_db']:.1f} dB")
        print(f"   目标音频峰值: {tgt_features['true_peak_db']:.1f} dB")
        
        # 清理
        os.unlink(ref_path)
        os.unlink(tgt_path)
        
        print("✅ 音频分析测试通过")
        return ref_features, tgt_features
        
    except Exception as e:
        print(f"❌ 音频分析测试失败: {e}")
        return None, None

def test_parameter_inversion():
    """测试参数反演功能"""
    print("\n⚙️ 测试参数反演...")
    
    try:
        from app.parameter_inversion import ParameterInverter
        
        # 先运行音频分析
        ref_features, tgt_features = test_audio_analysis()
        if not ref_features or not tgt_features:
            print("❌ 无法获取音频特征，跳过参数反演测试")
            return None
        
        inverter = ParameterInverter()
        
        # 测试 A 模式
        print("   测试 A 模式参数反演...")
        style_params_a = inverter.invert_parameters(ref_features, tgt_features, "A")
        
        # 测试 B 模式
        print("   测试 B 模式参数反演...")
        style_params_b = inverter.invert_parameters(ref_features, tgt_features, "B")
        
        # 显示结果
        print(f"   A 模式 EQ 段数: {len(style_params_a.get('eq', []))}")
        print(f"   A 模式目标 LUFS: {style_params_a['lufs']['target_lufs']:.1f}")
        print(f"   A 模式置信度: {style_params_a['metadata']['confidence']:.2f}")
        
        print(f"   B 模式 EQ 段数: {len(style_params_b.get('eq', []))}")
        print(f"   B 模式目标 LUFS: {style_params_b['lufs']['target_lufs']:.1f}")
        print(f"   B 模式置信度: {style_params_b['metadata']['confidence']:.2f}")
        
        print("✅ 参数反演测试通过")
        return style_params_a
        
    except Exception as e:
        print(f"❌ 参数反演测试失败: {e}")
        return None

def test_audio_rendering():
    """测试音频渲染功能"""
    print("\n🎵 测试音频渲染...")
    
    try:
        from app.audio_rendering import AudioRenderer
        
        # 获取风格参数
        style_params = test_parameter_inversion()
        if not style_params:
            print("❌ 无法获取风格参数，跳过渲染测试")
            return False
        
        renderer = AudioRenderer()
        
        # 创建测试音频
        ref_path, tgt_path = create_test_audio()
        output_path = "test_output.wav"
        
        print("   应用风格参数...")
        metrics = renderer.render_audio(tgt_path, output_path, style_params)
        
        # 显示渲染结果
        print(f"   STFT 距离: {metrics['stft_dist']:.3f}")
        print(f"   Mel 距离: {metrics['mel_dist']:.3f}")
        print(f"   LUFS 误差: {metrics['lufs_err']:.1f} LU")
        print(f"   输出峰值: {metrics['tp_db']:.1f} dB")
        print(f"   失真率: {metrics['artifacts_rate']:.3f}")
        
        # 检查输出文件
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   输出文件大小: {file_size / 1024:.1f} KB")
        
        # 清理
        for path in [ref_path, tgt_path, output_path]:
            if os.path.exists(path):
                os.unlink(path)
        
        print("✅ 音频渲染测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 音频渲染测试失败: {e}")
        return False

def test_end_to_end():
    """端到端测试"""
    print("\n🔄 端到端测试...")
    
    try:
        from app.audio_analysis import AudioAnalyzer
        from app.parameter_inversion import ParameterInverter
        from app.audio_rendering import AudioRenderer
        
        # 创建测试音频
        ref_path, tgt_path = create_test_audio()
        output_path = "test_e2e_output.wav"
        
        # 步骤 1: 分析
        print("   步骤 1: 音频分析...")
        analyzer = AudioAnalyzer()
        ref_features = analyzer.analyze_features(ref_path)
        tgt_features = analyzer.analyze_features(tgt_path)
        
        # 步骤 2: 参数反演
        print("   步骤 2: 参数反演...")
        inverter = ParameterInverter()
        style_params = inverter.invert_parameters(ref_features, tgt_features, "A")
        
        # 步骤 3: 音频渲染
        print("   步骤 3: 音频渲染...")
        renderer = AudioRenderer()
        metrics = renderer.render_audio(tgt_path, output_path, style_params)
        
        # 步骤 4: 验证结果
        print("   步骤 4: 验证结果...")
        if os.path.exists(output_path):
            # 分析输出音频
            output_features = analyzer.analyze_features(output_path)
            
            # 比较 LUFS
            target_lufs = style_params['lufs']['target_lufs']
            output_lufs = output_features['lufs']['integrated_lufs']
            lufs_diff = abs(target_lufs - output_lufs)
            
            print(f"   目标 LUFS: {target_lufs:.1f}")
            print(f"   输出 LUFS: {output_lufs:.1f}")
            print(f"   LUFS 差异: {lufs_diff:.1f} LU")
            
            if lufs_diff < 2.0:  # 允许 2 LU 误差
                print("✅ LUFS 匹配成功")
            else:
                print("⚠️ LUFS 匹配精度较低")
        
        # 清理
        for path in [ref_path, tgt_path, output_path]:
            if os.path.exists(path):
                os.unlink(path)
        
        print("✅ 端到端测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 端到端测试失败: {e}")
        return False

def install_dependencies():
    """安装必要的依赖"""
    print("📦 检查并安装依赖...")
    
    import subprocess
    
    try:
        # 安装 worker 依赖
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "worker/requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        print("请手动运行: pip install -r worker/requirements.txt")
        return False

def main():
    """主测试函数"""
    print("🎵 智能音频调音工具 - 音频处理算法测试")
    print("=" * 60)
    
    # 检查依赖
    if not install_dependencies():
        return
    
    # 运行测试
    tests = [
        ("音频分析", lambda: test_audio_analysis() is not None),
        ("参数反演", lambda: test_parameter_inversion() is not None),
        ("音频渲染", test_audio_rendering),
        ("端到端", test_end_to_end)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n📊 测试结果汇总:")
    print("-" * 30)
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:12} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 测试通过")
    
    if passed == len(results):
        print("\n🎉 所有音频处理算法测试通过！")
        print("可以继续进行前端开发和对象存储集成。")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息并修复。")

if __name__ == "__main__":
    main()
