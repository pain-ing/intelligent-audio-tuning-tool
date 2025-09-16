#!/usr/bin/env python3
"""
音频格式转换功能测试脚本
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
                          sample_rate: int = 44100, channels: int = 2):
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
    
    # 保存为WAV文件
    sf.write(file_path, audio_data, sample_rate)
    return file_path


def test_audio_format_converter():
    """测试音频格式转换器"""
    print("🎵 测试音频格式转换器")
    print("-" * 40)
    
    try:
        from worker.app.audio_format_converter import (
            AudioFormatConverter, AudioFormat, AudioQuality, ConversionSettings
        )
        
        # 创建转换器
        converter = AudioFormatConverter()
        print("✅ 音频格式转换器创建成功")
        
        # 创建测试音频文件
        temp_dir = tempfile.mkdtemp(prefix="format_test_")
        test_wav = os.path.join(temp_dir, "test_audio.wav")
        create_test_audio_file(test_wav, duration=1.0)
        print(f"✅ 测试音频文件创建成功: {test_wav}")
        
        try:
            # 测试元数据获取
            metadata = converter.get_audio_metadata(test_wav)
            print(f"✅ 元数据获取成功: {metadata.duration:.1f}s, {metadata.sample_rate}Hz, {metadata.channels}ch")
            
            # 测试格式支持检查
            assert converter.is_format_supported(test_wav, for_input=True)
            print("✅ 格式支持检查通过")
            
            # 测试WAV到FLAC转换
            output_flac = os.path.join(temp_dir, "test_output.flac")
            settings = ConversionSettings(
                target_format=AudioFormat.FLAC,
                quality=AudioQuality.HIGH,
                normalize=True
            )
            
            result = converter.convert_audio(test_wav, output_flac, settings)
            assert result["success"]
            assert os.path.exists(output_flac)
            print("✅ WAV到FLAC转换成功")
            
            # 测试转换估算
            estimate = converter.get_conversion_estimate(test_wav, settings)
            print(f"✅ 转换估算: 预计大小 {estimate['estimated_output_size']} 字节, "
                  f"预计时间 {estimate['estimated_processing_time']:.1f}秒")
            
            return True
            
        finally:
            # 清理测试文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 清理测试目录: {temp_dir}")
        
    except Exception as e:
        print(f"❌ 音频格式转换器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversion_settings():
    """测试转换设置"""
    print("\n⚙️ 测试转换设置")
    print("-" * 40)
    
    try:
        from worker.app.audio_format_converter import (
            AudioFormatConverter, AudioFormat, AudioQuality, ConversionSettings
        )
        
        converter = AudioFormatConverter()
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="settings_test_")
        test_wav = os.path.join(temp_dir, "test_stereo.wav")
        create_test_audio_file(test_wav, duration=0.5, channels=2)
        
        try:
            # 测试重采样
            output_resampled = os.path.join(temp_dir, "resampled.wav")
            settings = ConversionSettings(
                target_format=AudioFormat.WAV,
                target_sample_rate=22050,
                target_channels=1,  # 转为单声道
                normalize=True
            )
            
            result = converter.convert_audio(test_wav, output_resampled, settings)
            assert result["success"]
            
            # 验证输出
            output_metadata = result["output_metadata"]
            assert output_metadata.sample_rate == 22050
            assert output_metadata.channels == 1
            print("✅ 重采样和声道转换测试通过")
            
            # 测试淡入淡出
            output_fade = os.path.join(temp_dir, "fade.wav")
            settings = ConversionSettings(
                target_format=AudioFormat.WAV,
                fade_in=0.1,
                fade_out=0.1,
                trim_silence=True
            )
            
            result = converter.convert_audio(test_wav, output_fade, settings)
            assert result["success"]
            print("✅ 淡入淡出效果测试通过")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 转换设置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_conversion():
    """测试批量转换"""
    print("\n📦 测试批量转换")
    print("-" * 40)
    
    try:
        from worker.app.audio_format_converter import (
            AudioFormatConverter, AudioFormat, ConversionSettings
        )
        
        converter = AudioFormatConverter()
        
        # 创建多个测试文件
        temp_dir = tempfile.mkdtemp(prefix="batch_test_")
        test_files = []
        
        for i in range(3):
            test_file = os.path.join(temp_dir, f"test_{i+1}.wav")
            create_test_audio_file(test_file, duration=0.3)
            test_files.append(test_file)
        
        print(f"✅ 创建了 {len(test_files)} 个测试文件")
        
        try:
            # 准备批量转换
            file_pairs = []
            for i, input_file in enumerate(test_files):
                output_file = os.path.join(temp_dir, f"output_{i+1}.flac")
                file_pairs.append((input_file, output_file))
            
            settings = ConversionSettings(
                target_format=AudioFormat.FLAC,
                normalize=True
            )
            
            # 执行批量转换
            results = converter.batch_convert(file_pairs, settings)
            
            # 验证结果
            successful = sum(1 for r in results if r.get("success", False))
            print(f"✅ 批量转换完成: {successful}/{len(results)} 成功")
            
            # 检查输出文件
            for _, output_file in file_pairs:
                assert os.path.exists(output_file), f"输出文件不存在: {output_file}"
            
            print("✅ 所有输出文件验证通过")
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 批量转换测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_format_support():
    """测试格式支持"""
    print("\n📋 测试格式支持")
    print("-" * 40)
    
    try:
        from worker.app.audio_format_converter import AudioFormatConverter, AudioFormat
        
        converter = AudioFormatConverter()
        
        # 测试输入格式支持
        test_files = [
            "test.wav", "test.mp3", "test.flac", "test.aac", 
            "test.ogg", "test.m4a", "test.aiff"
        ]
        
        supported_count = 0
        for test_file in test_files:
            if converter.is_format_supported(test_file, for_input=True):
                supported_count += 1
        
        print(f"✅ 支持的输入格式: {supported_count}/{len(test_files)}")
        
        # 测试输出格式
        output_formats = list(AudioFormat)
        print(f"✅ 支持的输出格式: {len(output_formats)} 种")
        
        for format_enum in output_formats:
            extensions = converter.supported_output_formats.get(format_enum, [])
            print(f"   {format_enum.value}: {extensions}")
        
        return True
        
    except Exception as e:
        print(f"❌ 格式支持测试失败: {e}")
        return False


def test_quality_settings():
    """测试质量设置"""
    print("\n🎚️ 测试质量设置")
    print("-" * 40)
    
    try:
        from worker.app.audio_format_converter import (
            AudioFormatConverter, AudioFormat, AudioQuality, ConversionSettings
        )
        
        converter = AudioFormatConverter()
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="quality_test_")
        test_wav = os.path.join(temp_dir, "test.wav")
        create_test_audio_file(test_wav, duration=0.5)
        
        try:
            # 测试不同质量级别
            quality_levels = [AudioQuality.LOW, AudioQuality.MEDIUM, 
                            AudioQuality.HIGH, AudioQuality.LOSSLESS]
            
            results = {}
            
            for quality in quality_levels:
                output_file = os.path.join(temp_dir, f"quality_{quality.value}.wav")
                settings = ConversionSettings(
                    target_format=AudioFormat.WAV,
                    quality=quality
                )
                
                result = converter.convert_audio(test_wav, output_file, settings)
                assert result["success"]
                
                output_metadata = result["output_metadata"]
                results[quality.value] = {
                    "sample_rate": output_metadata.sample_rate,
                    "bit_depth": output_metadata.bit_depth,
                    "file_size": output_metadata.file_size
                }
            
            # 显示质量对比
            print("✅ 质量级别对比:")
            for quality, info in results.items():
                print(f"   {quality}: {info['sample_rate']}Hz, "
                      f"{info['bit_depth']}bit, {info['file_size']} bytes")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 质量设置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration_with_batch_processor():
    """测试与批处理器的集成"""
    print("\n🔗 测试与批处理器集成")
    print("-" * 40)
    
    try:
        from worker.app.audio_format_converter import AudioFormat, ConversionSettings
        from worker.app.batch_processor import global_batch_processor
        from worker.app.batch_models import BatchTask, AudioProcessingParams
        
        # 创建测试文件
        temp_dir = tempfile.mkdtemp(prefix="integration_test_")
        test_wav = os.path.join(temp_dir, "test.wav")
        create_test_audio_file(test_wav, duration=0.3)
        
        try:
            # 创建格式转换任务
            output_flac = os.path.join(temp_dir, "output.flac")
            
            # 创建包含格式转换信息的处理参数
            processing_params = AudioProcessingParams(
                style_params={
                    "format_conversion": {
                        "target_format": AudioFormat.FLAC.value,
                        "quality": "high",
                        "normalize": True
                    }
                },
                output_format="flac",
                normalize_audio=True
            )
            
            task = BatchTask(
                input_path=test_wav,
                output_path=output_flac,
                processing_params=processing_params
            )
            
            # 提交到批处理器
            batch_id = global_batch_processor.submit_batch([task])
            print(f"✅ 格式转换任务提交到批处理器: {batch_id}")
            
            # 检查状态
            status = global_batch_processor.get_batch_status(batch_id)
            assert status is not None
            print("✅ 批处理状态查询成功")
            
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"❌ 批处理器集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🚀 音频格式转换功能测试")
    print("=" * 60)
    
    tests = [
        ("音频格式转换器", test_audio_format_converter),
        ("转换设置", test_conversion_settings),
        ("批量转换", test_batch_conversion),
        ("格式支持", test_format_support),
        ("质量设置", test_quality_settings),
        ("批处理器集成", test_integration_with_batch_processor)
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
    print("📋 音频格式转换功能测试结果总结")
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
        print("🎉 音频格式转换功能 - 所有测试通过！")
        print("✅ 音频格式转换集成功能已准备就绪")
        return True
    else:
        print("⚠️ 部分测试失败，需要进一步调试")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
