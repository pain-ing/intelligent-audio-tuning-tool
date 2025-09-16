#!/usr/bin/env python3
"""
Adobe Audition集成验证脚本
用于验证集成的基本功能和配置
"""

import os
import sys
import json
import time
import logging
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_installation():
    """验证Adobe Audition安装"""
    logger.info("=== 验证Adobe Audition安装 ===")
    
    detector = AuditionDetector()
    
    # 检测安装
    is_installed = detector.detect_installation()
    
    if is_installed:
        logger.info("✓ Adobe Audition已安装")
        info = detector.get_installation_info()
        logger.info(f"  路径: {info['executable_path']}")
        logger.info(f"  版本: {info['version']}")
        logger.info(f"  平台: {info['platform']}")
        if 'file_size' in info:
            logger.info(f"  文件大小: {info['file_size'] / 1024 / 1024:.1f} MB")
    else:
        logger.warning("✗ 未检测到Adobe Audition安装")
        logger.info("  支持的平台: Windows, macOS")
        logger.info("  当前平台: " + detector.platform)
    
    return is_installed


def validate_configuration():
    """验证配置管理"""
    logger.info("=== 验证配置管理 ===")
    
    try:
        config_manager = AuditionConfigManager()
        config = config_manager.config
        
        logger.info("✓ 配置管理器初始化成功")
        logger.info(f"  启用状态: {config.enabled}")
        logger.info(f"  超时设置: {config.timeout_seconds}秒")
        logger.info(f"  回退模式: {config.fallback_to_default}")
        logger.info(f"  脚本模式: {config.use_script_mode}")
        
        # 测试配置验证
        validation = config_manager.validate_config()
        if validation["valid"]:
            logger.info("✓ 配置验证通过")
        else:
            logger.warning("✗ 配置验证失败")
            for error in validation["errors"]:
                logger.warning(f"  错误: {error}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 配置管理验证失败: {e}")
        return False


def validate_parameter_conversion():
    """验证参数转换"""
    logger.info("=== 验证参数转换 ===")
    
    try:
        converter = AuditionParameterConverter()
        
        # 测试样例参数
        test_params = {
            "eq": {
                "bands": [
                    {"freq": 100, "gain": -2.0, "q": 0.7, "type": "highpass"},
                    {"freq": 1000, "gain": 3.0, "q": 1.0, "type": "peak"},
                    {"freq": 8000, "gain": -1.5, "q": 1.5, "type": "peak"}
                ]
            },
            "compression": {
                "threshold": -18,
                "ratio": 3.0,
                "attack": 5,
                "release": 50
            },
            "reverb": {
                "wet_level": 0.25,
                "dry_level": 0.75,
                "pre_delay": 20
            },
            "limiter": {
                "ceiling": -0.3,
                "release": 75
            }
        }
        
        # 转换参数
        start_time = time.time()
        audition_params = converter.convert_style_params(test_params)
        conversion_time = time.time() - start_time
        
        logger.info("✓ 参数转换成功")
        logger.info(f"  转换时间: {conversion_time:.3f}秒")
        logger.info(f"  支持的效果: {len(audition_params) - 2}")  # 减去内部参数
        
        # 显示转换日志
        if "_conversion_log" in audition_params:
            logger.info("  转换日志:")
            for log_entry in audition_params["_conversion_log"]:
                logger.info(f"    {log_entry}")
        
        # 验证参数
        validation = converter.validate_style_params(test_params)
        logger.info(f"  参数验证: {'通过' if validation['valid'] else '失败'}")
        logger.info(f"  支持的参数: {len(validation['supported_params'])}")
        logger.info(f"  不支持的参数: {len(validation['unsupported_params'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 参数转换验证失败: {e}")
        return False


def validate_template_generation():
    """验证模板生成"""
    logger.info("=== 验证模板生成 ===")
    
    try:
        # 使用临时目录
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AuditionTemplateManager(temp_dir)
            
            # 测试参数
            test_params = {
                "eq": {
                    "bands": [{"freq": 1000, "gain": 3.0, "q": 1.0, "type": "peak"}]
                },
                "compression": {
                    "threshold": -20,
                    "ratio": 4.0
                }
            }
            
            # 生成脚本
            input_file = "test_input.wav"
            output_file = "test_output.wav"
            
            script_path = manager.create_processing_script(
                input_file, output_file, test_params
            )
            
            logger.info("✓ 脚本生成成功")
            logger.info(f"  脚本路径: {script_path}")
            
            # 检查脚本内容
            if os.path.exists(script_path):
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                logger.info(f"  脚本大小: {len(content)}字符")
                logger.info("  脚本包含:")
                
                checks = [
                    ("主函数", "function main()" in content),
                    ("错误处理", "try {" in content and "catch" in content),
                    ("进度报告", "reportProgress" in content),
                    ("日志记录", "logInfo" in content),
                    ("效果应用", "应用效果" in content)
                ]
                
                for check_name, check_result in checks:
                    status = "✓" if check_result else "✗"
                    logger.info(f"    {status} {check_name}")
            
            # 测试模板信息
            template_info = manager.get_template_info()
            logger.info(f"  模板目录: {template_info['template_directory']}")
            logger.info(f"  基础模板存在: {template_info['base_template_exists']}")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ 模板生成验证失败: {e}")
        return False


def validate_integration():
    """验证整体集成"""
    logger.info("=== 验证整体集成 ===")
    
    try:
        # 测试渲染器创建
        from worker.app.audio_rendering import create_audio_renderer
        
        # 测试Adobe Audition渲染器
        audition_renderer = create_audio_renderer(renderer_type="audition")
        logger.info(f"✓ 渲染器创建成功: {audition_renderer.renderer_type}")
        
        if hasattr(audition_renderer, 'audition_renderer') and audition_renderer.audition_renderer:
            logger.info("  Adobe Audition渲染器已启用")
        else:
            logger.info("  使用默认渲染器（Adobe Audition不可用）")
        
        # 测试默认渲染器
        default_renderer = create_audio_renderer(renderer_type="default")
        logger.info(f"✓ 默认渲染器创建成功: {default_renderer.renderer_type}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 整体集成验证失败: {e}")
        return False


def main():
    """主验证函数"""
    logger.info("开始Adobe Audition集成验证")
    logger.info("=" * 50)
    
    results = {
        "installation": validate_installation(),
        "configuration": validate_configuration(),
        "parameter_conversion": validate_parameter_conversion(),
        "template_generation": validate_template_generation(),
        "integration": validate_integration()
    }
    
    logger.info("=" * 50)
    logger.info("验证结果汇总:")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"  {test_name}: {status}")
    
    logger.info(f"总计: {passed_tests}/{total_tests} 项测试通过")
    
    if passed_tests == total_tests:
        logger.info("🎉 所有验证项目都通过了！")
        return 0
    else:
        logger.warning("⚠️  部分验证项目失败，请检查配置和安装")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
