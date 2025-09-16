#!/usr/bin/env python3
"""
简单的Adobe Audition集成测试脚本
不依赖pytest，直接运行基础功能测试
"""

import os
import sys
import tempfile
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from worker.app.audition_integration import (
    AuditionDetector,
    AuditionParameterConverter,
    AuditionTemplateManager
)
from src.core.audition_config import AuditionConfigManager


def test_audition_detector():
    """测试Adobe Audition检测器"""
    print("测试 AuditionDetector...")
    
    detector = AuditionDetector()
    
    # 测试基本属性
    assert detector.platform in ["windows", "darwin", "linux"], "平台检测失败"
    assert isinstance(detector.audition_paths, list), "路径列表类型错误"
    
    # 测试检测功能
    is_installed = detector.detect_installation()
    print(f"  检测结果: {'已安装' if is_installed else '未安装'}")
    
    # 测试安装信息
    info = detector.get_installation_info()
    assert isinstance(info, dict), "安装信息类型错误"
    assert "installed" in info, "安装信息缺少installed字段"
    
    print("  ✓ AuditionDetector 测试通过")


def test_parameter_converter():
    """测试参数转换器"""
    print("测试 AuditionParameterConverter...")
    
    converter = AuditionParameterConverter()
    
    # 测试基本功能
    supported = converter.get_supported_parameters()
    assert isinstance(supported, list), "支持参数列表类型错误"
    assert "eq" in supported, "缺少EQ支持"
    assert "compression" in supported, "缺少压缩支持"
    
    # 测试参数转换
    test_params = {
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
    
    result = converter.convert_style_params(test_params)
    assert isinstance(result, dict), "转换结果类型错误"
    assert "eq" in result, "转换结果缺少EQ"
    assert "compression" in result, "转换结果缺少压缩"
    assert "_conversion_log" in result, "转换结果缺少日志"
    
    # 测试参数验证
    validation = converter.validate_style_params(test_params)
    assert validation["valid"] is True, "参数验证失败"
    assert len(validation["supported_params"]) == 2, "支持参数数量错误"
    
    print("  ✓ AuditionParameterConverter 测试通过")


def test_template_manager():
    """测试模板管理器"""
    print("测试 AuditionTemplateManager...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = AuditionTemplateManager(temp_dir)
        
        # 测试脚本生成
        test_params = {
            "eq": {"bands": [{"freq": 1000, "gain": 3}]},
            "compression": {"threshold": -20, "ratio": 4.0}
        }
        
        script_path = manager.create_processing_script(
            "input.wav", "output.wav", test_params
        )
        
        assert os.path.exists(script_path), "脚本文件未生成"
        assert script_path.endswith('.jsx'), "脚本文件扩展名错误"
        
        # 检查脚本内容
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "function main()" in content, "脚本缺少主函数"
            assert "try {" in content, "脚本缺少错误处理"
            assert "应用效果" in content, "脚本缺少效果应用"
        
        # 测试模板信息
        info = manager.get_template_info()
        assert isinstance(info, dict), "模板信息类型错误"
        assert "template_directory" in info, "模板信息缺少目录"
        
        print("  ✓ AuditionTemplateManager 测试通过")


def test_config_manager():
    """测试配置管理器"""
    print("测试 AuditionConfigManager...")
    
    config_manager = AuditionConfigManager()
    config = config_manager.config
    
    # 测试配置属性
    assert hasattr(config, 'enabled'), "配置缺少enabled属性"
    assert hasattr(config, 'timeout_seconds'), "配置缺少timeout_seconds属性"
    assert hasattr(config, 'fallback_to_default'), "配置缺少fallback_to_default属性"
    
    # 测试配置验证
    validation = config_manager.validate_config()
    assert isinstance(validation, dict), "配置验证结果类型错误"
    assert "valid" in validation, "配置验证结果缺少valid字段"
    
    print("  ✓ AuditionConfigManager 测试通过")


def test_integration():
    """测试整体集成"""
    print("测试整体集成...")
    
    try:
        from worker.app.audio_rendering import create_audio_renderer
        
        # 测试渲染器创建
        audition_renderer = create_audio_renderer(renderer_type="audition")
        assert audition_renderer is not None, "Adobe Audition渲染器创建失败"
        
        default_renderer = create_audio_renderer(renderer_type="default")
        assert default_renderer is not None, "默认渲染器创建失败"
        
        print("  ✓ 整体集成测试通过")
        
    except Exception as e:
        print(f"  ✗ 整体集成测试失败: {e}")
        raise


def run_performance_test():
    """运行性能测试"""
    print("运行性能测试...")
    
    converter = AuditionParameterConverter()
    
    # 测试大参数集转换性能
    large_params = {
        "eq": {
            "bands": [
                {"freq": 100 + i * 100, "gain": (i % 10) - 5, "q": 1.0, "type": "peak"}
                for i in range(20)  # 20个频段
            ]
        }
    }
    
    start_time = time.time()
    result = converter.convert_style_params(large_params)
    end_time = time.time()
    
    conversion_time = end_time - start_time
    assert conversion_time < 1.0, f"转换时间过长: {conversion_time:.3f}秒"
    
    print(f"  ✓ 大参数集转换性能测试通过 ({conversion_time:.3f}秒)")


def main():
    """运行所有测试"""
    print("开始Adobe Audition集成基础功能测试")
    print("=" * 50)
    
    tests = [
        ("Adobe Audition检测器", test_audition_detector),
        ("参数转换器", test_parameter_converter),
        ("模板管理器", test_template_manager),
        ("配置管理器", test_config_manager),
        ("整体集成", test_integration),
        ("性能测试", run_performance_test)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✓ {test_name} - 通过")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} - 失败: {e}")
    
    print("=" * 50)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试都通过了！")
        return 0
    else:
        print("⚠️ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
