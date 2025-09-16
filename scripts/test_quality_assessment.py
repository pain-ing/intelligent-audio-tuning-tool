#!/usr/bin/env python3
"""
音频质量评估系统测试脚本
"""

import os
import sys
import tempfile
import shutil
import numpy as np
import soundfile as sf
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_test_audio_file(file_path: str, duration: float = 2.0,
                          sample_rate: int = 44100, channels: int = 2,
                          add_noise: bool = False, add_distortion: bool = False,
                          quality_level: str = "high"):
    """创建测试音频文件"""
    # 生成测试音频数据（正弦波）
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 440  # A4音符

    if channels == 1:
        audio_data = np.sin(2 * np.pi * frequency * t)
    else:
        # 立体声：左声道440Hz，右声道880Hz
        left_channel = np.sin(2 * np.pi * frequency * t)
        right_channel = np.sin(2 * np.pi * (frequency * 2) * t)
        audio_data = np.column_stack([left_channel, right_channel])

    # 根据质量级别添加不同程度的噪声底噪
    if quality_level == "high":
        # 高质量：添加极小的噪声底噪 (-60dB)
        noise_level = 0.001
        if channels == 1:
            noise = np.random.normal(0, noise_level, audio_data.shape)
        else:
            noise = np.random.normal(0, noise_level, audio_data.shape)
        audio_data += noise

    # 添加噪声
    if add_noise:
        noise_level = 0.05  # -26dB噪声
        if channels == 1:
            noise = np.random.normal(0, noise_level, audio_data.shape)
        else:
            noise = np.random.normal(0, noise_level, audio_data.shape)
        audio_data += noise

    # 添加失真
    if add_distortion:
        # 简单的削波失真
        audio_data = np.clip(audio_data * 1.5, -0.8, 0.8)

    # 保存为WAV文件
    sf.write(file_path, audio_data, sample_rate)
    return file_path


def test_quality_analyzer():
    """测试音频质量分析器"""
    print("🎵 测试音频质量分析器")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        # 创建分析器
        analyzer = AudioQualityAnalyzer()
        print("✅ 音频质量分析器创建成功")
        
        # 创建测试音频文件
        temp_dir = tempfile.mkdtemp(prefix="quality_test_")
        test_wav = os.path.join(temp_dir, "test_audio.wav")
        create_test_audio_file(test_wav, duration=1.0)
        print(f"✅ 测试音频文件创建成功: {test_wav}")
        
        try:
            # 测试质量分析
            metrics = analyzer.analyze_audio_quality(test_wav)
            print(f"✅ 质量分析成功:")
            print(f"   信噪比: {metrics.snr:.1f} dB")
            print(f"   总谐波失真: {metrics.thd:.2f}%")
            print(f"   动态范围: {metrics.dynamic_range:.1f} dB")
            print(f"   响度: {metrics.loudness_lufs:.1f} LUFS")
            print(f"   感知质量评分: {metrics.perceived_quality_score:.1f}")
            
            # 验证基本指标
            assert metrics.duration > 0
            assert metrics.sample_rate > 0
            assert metrics.channels > 0
            assert 0 <= metrics.perceived_quality_score <= 100
            print("✅ 质量指标验证通过")
            
            return True
            
        finally:
            # 清理测试文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 清理测试目录: {temp_dir}")
        
    except Exception as e:
        print(f"❌ 音频质量分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_comparison():
    """测试音频质量对比"""
    print("\n🔍 测试音频质量对比")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        analyzer = AudioQualityAnalyzer()
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="comparison_test_")
        
        # 原始文件（高质量）
        original_file = os.path.join(temp_dir, "original.wav")
        create_test_audio_file(original_file, duration=1.0, add_noise=False, add_distortion=False)
        
        # 处理后文件（添加噪声和失真）
        processed_file = os.path.join(temp_dir, "processed.wav")
        create_test_audio_file(processed_file, duration=1.0, add_noise=True, add_distortion=True)
        
        print("✅ 创建了原始和处理后的测试文件")
        
        try:
            # 执行质量对比
            comparison = analyzer.compare_audio_quality(original_file, processed_file)
            
            print(f"✅ 质量对比完成:")
            print(f"   信噪比变化: {comparison.snr_change:.1f} dB")
            print(f"   总谐波失真变化: {comparison.thd_change:.2f}%")
            print(f"   动态范围变化: {comparison.dynamic_range_change:.1f} dB")
            print(f"   整体质量变化: {comparison.overall_quality_change:.1f}")
            print(f"   质量等级: {comparison.quality_grade}")
            
            # 验证对比结果
            assert comparison.original_metrics is not None
            assert comparison.processed_metrics is not None
            assert isinstance(comparison.improvements, list)
            assert isinstance(comparison.degradations, list)
            assert isinstance(comparison.recommendations, list)
            
            print("✅ 质量对比验证通过")
            
            # 显示改进和退化
            if comparison.improvements:
                print(f"   改进项目: {', '.join(comparison.improvements)}")
            if comparison.degradations:
                print(f"   退化项目: {', '.join(comparison.degradations)}")
            if comparison.recommendations:
                print(f"   建议: {', '.join(comparison.recommendations[:2])}")  # 只显示前2个建议
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 音频质量对比测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_metrics():
    """测试各种质量指标"""
    print("\n📊 测试质量指标计算")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        analyzer = AudioQualityAnalyzer()
        
        # 创建不同质量的测试文件
        temp_dir = tempfile.mkdtemp(prefix="metrics_test_")
        
        test_cases = [
            ("高质量", False, False, "high"),
            ("有噪声", True, False, "medium"),
            ("有失真", False, True, "medium"),
            ("低质量", True, True, "low")
        ]

        results = {}

        for name, add_noise, add_distortion, quality_level in test_cases:
            test_file = os.path.join(temp_dir, f"{name}.wav")
            create_test_audio_file(test_file, duration=0.5,
                                 add_noise=add_noise, add_distortion=add_distortion,
                                 quality_level=quality_level)
            
            metrics = analyzer.analyze_audio_quality(test_file)
            results[name] = metrics
            
            print(f"✅ {name}音频分析完成:")
            print(f"   SNR: {metrics.snr:.1f}dB, THD: {metrics.thd:.2f}%, "
                  f"DR: {metrics.dynamic_range:.1f}dB, 评分: {metrics.perceived_quality_score:.1f}")
        
        # 验证质量趋势
        high_quality = results["高质量"]
        low_quality = results["低质量"]
        
        # 高质量应该有更好的指标
        assert high_quality.perceived_quality_score > low_quality.perceived_quality_score
        assert high_quality.snr > low_quality.snr
        print("✅ 质量趋势验证通过")
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True
        
    except Exception as e:
        print(f"❌ 质量指标测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stereo_analysis():
    """测试立体声分析"""
    print("\n🎧 测试立体声分析")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        analyzer = AudioQualityAnalyzer()
        
        temp_dir = tempfile.mkdtemp(prefix="stereo_test_")
        
        try:
            # 创建立体声测试文件
            stereo_file = os.path.join(temp_dir, "stereo.wav")
            create_test_audio_file(stereo_file, duration=0.5, channels=2)
            
            # 创建单声道测试文件
            mono_file = os.path.join(temp_dir, "mono.wav")
            create_test_audio_file(mono_file, duration=0.5, channels=1)
            
            # 分析立体声文件
            stereo_metrics = analyzer.analyze_audio_quality(stereo_file)
            print(f"✅ 立体声分析:")
            print(f"   立体声宽度: {stereo_metrics.stereo_width:.2f}")
            print(f"   相位相关性: {stereo_metrics.phase_correlation:.2f}")
            print(f"   声道数: {stereo_metrics.channels}")
            
            # 分析单声道文件
            mono_metrics = analyzer.analyze_audio_quality(mono_file)
            print(f"✅ 单声道分析:")
            print(f"   立体声宽度: {mono_metrics.stereo_width:.2f}")
            print(f"   相位相关性: {mono_metrics.phase_correlation:.2f}")
            print(f"   声道数: {mono_metrics.channels}")
            
            # 验证立体声指标
            assert stereo_metrics.channels == 2
            assert mono_metrics.channels == 1
            assert 0 <= stereo_metrics.stereo_width <= 1
            assert -1 <= stereo_metrics.phase_correlation <= 1
            
            print("✅ 立体声分析验证通过")
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 立体声分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_grading():
    """测试质量等级评定"""
    print("\n🏆 测试质量等级评定")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        analyzer = AudioQualityAnalyzer()
        
        # 测试质量等级判定
        test_scores = [95, 80, 65, 45, 25]
        expected_grades = ["Excellent", "Good", "Fair", "Poor", "Very Poor"]
        
        for score, expected in zip(test_scores, expected_grades):
            # 创建模拟指标
            from worker.app.audio_quality_analyzer import QualityMetrics
            metrics = QualityMetrics(perceived_quality_score=score)
            
            grade = analyzer._determine_quality_grade(metrics)
            print(f"✅ 评分 {score} -> 等级 {grade}")
            
            assert grade == expected, f"期望 {expected}，实际 {grade}"
        
        print("✅ 质量等级评定验证通过")
        return True
        
    except Exception as e:
        print(f"❌ 质量等级评定测试失败: {e}")
        return False


def test_mfcc_features():
    """测试MFCC特征提取"""
    print("\n🎼 测试MFCC特征提取")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        analyzer = AudioQualityAnalyzer()
        
        temp_dir = tempfile.mkdtemp(prefix="mfcc_test_")
        
        try:
            # 创建测试文件
            test_file = os.path.join(temp_dir, "mfcc_test.wav")
            create_test_audio_file(test_file, duration=0.5)
            
            # 分析MFCC特征
            metrics = analyzer.analyze_audio_quality(test_file)
            
            print(f"✅ MFCC特征提取:")
            print(f"   特征数量: {len(metrics.mfcc_features)}")
            print(f"   前5个特征: {[f'{x:.2f}' for x in metrics.mfcc_features[:5]]}")
            
            # 验证MFCC特征
            assert len(metrics.mfcc_features) == 13  # 标准MFCC特征数量
            assert all(isinstance(x, float) for x in metrics.mfcc_features)
            
            print("✅ MFCC特征验证通过")
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ MFCC特征测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n⚠️ 测试错误处理")
    print("-" * 40)
    
    try:
        from worker.app.audio_quality_analyzer import AudioQualityAnalyzer
        
        analyzer = AudioQualityAnalyzer()
        
        # 测试不存在的文件
        try:
            analyzer.analyze_audio_quality("nonexistent_file.wav")
            assert False, "应该抛出FileNotFoundError"
        except FileNotFoundError:
            print("✅ 不存在文件错误处理正确")
        
        # 测试对比不存在的文件
        temp_dir = tempfile.mkdtemp(prefix="error_test_")
        try:
            test_file = os.path.join(temp_dir, "test.wav")
            create_test_audio_file(test_file, duration=0.3)
            
            try:
                analyzer.compare_audio_quality(test_file, "nonexistent.wav")
                assert False, "应该抛出异常"
            except:
                print("✅ 对比文件错误处理正确")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 音频质量评估系统测试")
    print("=" * 60)
    
    tests = [
        ("音频质量分析器", test_quality_analyzer),
        ("音频质量对比", test_quality_comparison),
        ("质量指标计算", test_quality_metrics),
        ("立体声分析", test_stereo_analysis),
        ("质量等级评定", test_quality_grading),
        ("MFCC特征提取", test_mfcc_features),
        ("错误处理", test_error_handling)
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
    print("📋 音频质量评估系统测试结果总结")
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
        print("🎉 音频质量评估系统 - 所有测试通过！")
        print("✅ 质量评估系统功能已准备就绪")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
