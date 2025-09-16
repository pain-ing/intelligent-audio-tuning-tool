"""
Adobe Audition集成测试
"""

import pytest
import os
import tempfile
import json
import time
import platform
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 导入测试目标
from worker.app.audition_integration import (
    AuditionDetector,
    AuditionParameterConverter,
    AuditionTemplateManager
)
from worker.app.audition_renderer import AuditionAudioRenderer
from src.core.audition_config import AuditionConfigManager, AuditionConfig


class TestAuditionDetector:
    """Adobe Audition检测器测试"""
    
    def test_detector_initialization(self):
        """测试检测器初始化"""
        detector = AuditionDetector()
        assert detector.platform in ["windows", "darwin", "linux"]
        assert isinstance(detector.audition_paths, list)
    
    @patch('os.path.exists')
    def test_detect_installation_success(self, mock_exists):
        """测试成功检测安装"""
        mock_exists.return_value = True
        
        detector = AuditionDetector()
        with patch.object(detector, '_get_version', return_value="2024.1"):
            result = detector.detect_installation()
            
        assert result is True
        assert detector.executable_path is not None
        assert detector.detected_version == "2024.1"
    
    @patch('os.path.exists')
    def test_detect_installation_failure(self, mock_exists):
        """测试检测安装失败"""
        mock_exists.return_value = False
        
        detector = AuditionDetector()
        result = detector.detect_installation()
        
        assert result is False
        assert detector.executable_path is None

    @patch('platform.system')
    def test_unsupported_platform(self, mock_system):
        """测试不支持的平台"""
        mock_system.return_value = "Linux"

        detector = AuditionDetector()
        result = detector.detect_installation()

        assert result is False
        assert detector.platform == "linux"

    @patch('os.path.exists')
    @patch.object(AuditionDetector, '_verify_executable')
    def test_verify_executable_validation(self, mock_verify, mock_exists):
        """测试可执行文件验证"""
        mock_exists.return_value = True
        mock_verify.return_value = True

        detector = AuditionDetector()
        with patch.object(detector, '_get_version', return_value="2023.1"):
            result = detector.detect_installation()

        assert result is True
        mock_verify.assert_called()

    def test_get_installation_info_not_installed(self):
        """测试获取未安装时的信息"""
        detector = AuditionDetector()
        info = detector.get_installation_info()

        assert info["installed"] is False
        assert "executable_path" not in info

    @patch('os.path.exists')
    @patch('os.stat')
    def test_get_installation_info_installed(self, mock_stat, mock_exists):
        """测试获取已安装时的信息"""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 1024000
        mock_stat.return_value.st_mtime = time.time()

        detector = AuditionDetector()
        detector.executable_path = "/test/path/audition.exe"
        detector.detected_version = "2024.1"

        info = detector.get_installation_info()

        assert info["installed"] is True
        assert info["executable_path"] == "/test/path/audition.exe"
        assert info["version"] == "2024.1"
        assert "file_size" in info
        assert "modified_time" in info


class TestAuditionParameterConverter:
    """Adobe Audition参数转换器测试"""
    
    def test_converter_initialization(self):
        """测试转换器初始化"""
        converter = AuditionParameterConverter()
        assert isinstance(converter.parameter_mapping, dict)
        assert "eq" in converter.parameter_mapping
        assert "compression" in converter.parameter_mapping
    
    def test_convert_style_params(self):
        """测试风格参数转换"""
        converter = AuditionParameterConverter()
        
        style_params = {
            "eq": {
                "bands": [
                    {"freq": 1000, "gain": 3.0, "q": 1.0, "type": "peak"}
                ]
            },
            "compression": {
                "threshold": -18,
                "ratio": 3.0,
                "attack": 5,
                "release": 50
            }
        }
        
        audition_params = converter.convert_style_params(style_params)
        
        assert "eq" in audition_params
        assert "compression" in audition_params
        assert audition_params["eq"]["bands"][0]["frequency"] == 1000
        assert audition_params["compression"]["threshold"] == -18
        assert "_conversion_log" in audition_params
        assert "_conversion_timestamp" in audition_params
    
    def test_convert_eq_bands(self):
        """测试EQ频段转换"""
        converter = AuditionParameterConverter()
        
        bands = [
            {"freq": 100, "gain": -2.0, "q": 0.7, "type": "highpass"},
            {"freq": 1000, "gain": 3.0, "q": 1.0, "type": "peak"}
        ]
        
        audition_bands = converter._convert_eq_bands(bands)
        
        assert len(audition_bands) == 2
        assert audition_bands[0]["frequency"] == 100
        assert audition_bands[1]["gain"] == 3.0


class TestAuditionTemplateManager:
    """Adobe Audition模板管理器测试"""
    
    def test_template_manager_initialization(self):
        """测试模板管理器初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AuditionTemplateManager(temp_dir)
            assert manager.template_dir == temp_dir
            assert os.path.exists(temp_dir)
    
    def test_create_processing_script(self):
        """测试创建处理脚本"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AuditionTemplateManager(temp_dir)
            
            audition_params = {
                "eq": {"bands": []},
                "compression": {"threshold": -20, "ratio": 4.0}
            }
            
            script_path = manager.create_processing_script(
                "input.wav", "output.wav", audition_params
            )
            
            assert os.path.exists(script_path)
            assert script_path.endswith(".jsx")
            
            # 检查脚本内容
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "input.wav" in content
                assert "output.wav" in content
    
    def test_generate_effects_code(self):
        """测试生成效果代码"""
        manager = AuditionTemplateManager()
        
        audition_params = {
            "compression": {"threshold": -15, "ratio": 3.0},
            "limiter": {"ceiling": -0.5, "release": 100}
        }
        
        effects_code = manager._generate_effects_code(audition_params)
        
        assert "Multiband Compressor" in effects_code
        assert "Adaptive Limiter" in effects_code
        assert "-15" in effects_code


class TestAuditionAudioRenderer:
    """Adobe Audition音频渲染器测试"""
    
    @patch('worker.app.audition_renderer.AuditionDetector')
    def test_renderer_initialization_success(self, mock_detector_class):
        """测试渲染器成功初始化"""
        mock_detector = Mock()
        mock_detector.detect_installation.return_value = True
        mock_detector.executable_path = "/path/to/audition"
        mock_detector.detected_version = "2024.1"
        mock_detector_class.return_value = mock_detector
        
        renderer = AuditionAudioRenderer()
        
        assert renderer.is_available is True
        assert renderer.audition_path == "/path/to/audition"
    
    @patch('worker.app.audition_renderer.AuditionDetector')
    def test_renderer_initialization_failure(self, mock_detector_class):
        """测试渲染器初始化失败"""
        mock_detector = Mock()
        mock_detector.detect_installation.return_value = False
        mock_detector_class.return_value = mock_detector
        
        renderer = AuditionAudioRenderer()
        
        assert renderer.is_available is False
    
    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_render_with_command_line(self, mock_exists, mock_subprocess):
        """测试命令行渲染"""
        mock_exists.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        
        renderer = AuditionAudioRenderer()
        renderer.is_available = True
        renderer.audition_path = "/path/to/audition"
        
        with patch.object(renderer, '_generate_basic_metrics', return_value={}):
            metrics = renderer._render_with_command_line(
                "input.wav", "output.wav", {"limiter": {"ceiling": -0.1}}
            )
            
        assert isinstance(metrics, dict)
        mock_subprocess.assert_called_once()
    
    def test_should_use_script_mode(self):
        """测试脚本模式判断"""
        renderer = AuditionAudioRenderer()
        renderer.is_available = True
        
        # 简单参数应该使用命令行
        simple_params = {"limiter": {"ceiling": -0.1}}
        assert renderer._should_use_script_mode(simple_params) is False
        
        # 复杂参数应该使用脚本
        complex_params = {
            "eq": {"bands": []},
            "compression": {"threshold": -20},
            "reverb": {"mix": 0.3}
        }
        assert renderer._should_use_script_mode(complex_params) is True


class TestAuditionConfigManager:
    """Adobe Audition配置管理器测试"""
    
    def test_config_manager_initialization(self):
        """测试配置管理器初始化"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            config_file = temp_file.name
        
        try:
            manager = AuditionConfigManager(config_file)
            assert manager.config_file == config_file
            assert isinstance(manager.config, AuditionConfig)
        finally:
            os.unlink(config_file)
    
    def test_save_and_load_config(self):
        """测试配置保存和加载"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            config_file = temp_file.name
        
        try:
            manager = AuditionConfigManager(config_file)
            
            # 更新配置
            manager.update_config(
                enabled=True,
                executable_path="/test/path",
                timeout_seconds=600
            )
            
            # 创建新的管理器实例加载配置
            new_manager = AuditionConfigManager(config_file)
            
            assert new_manager.config.enabled is True
            assert new_manager.config.executable_path == "/test/path"
            assert new_manager.config.timeout_seconds == 600
        finally:
            os.unlink(config_file)
    
    def test_validate_config(self):
        """测试配置验证"""
        manager = AuditionConfigManager()
        
        # 测试无效配置
        manager.update_config(enabled=True, executable_path=None)
        validation = manager.validate_config()
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0
        
        # 测试有效配置
        with tempfile.NamedTemporaryFile() as temp_file:
            manager.update_config(
                enabled=True,
                executable_path=temp_file.name
            )
            validation = manager.validate_config()
            assert validation["valid"] is True
    
    def test_is_file_supported(self):
        """测试文件支持检查"""
        manager = AuditionConfigManager()
        
        # 禁用状态下不支持任何文件
        manager.update_config(enabled=False)
        assert manager.is_file_supported("test.wav") is False
        
        # 启用状态下检查文件格式
        manager.update_config(enabled=True, executable_path="/test/path")
        
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
            assert manager.is_file_supported(temp_file.name) is True
        
        with tempfile.NamedTemporaryFile(suffix='.txt') as temp_file:
            assert manager.is_file_supported(temp_file.name) is False


@pytest.fixture
def sample_audio_file():
    """创建示例音频文件"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        # 创建简单的WAV文件头（实际测试中可能需要真实的音频数据）
        temp_file.write(b'RIFF' + b'\x00' * 44)  # 简化的WAV头
        yield temp_file.name
    os.unlink(temp_file.name)


class TestIntegration:
    """集成测试"""
    
    @patch('worker.app.audition_integration.AuditionDetector.detect_installation')
    def test_end_to_end_workflow(self, mock_detect, sample_audio_file):
        """测试端到端工作流"""
        mock_detect.return_value = False  # 模拟未安装Adobe Audition
        
        # 测试配置管理
        manager = AuditionConfigManager()
        assert manager.config.enabled is False
        
        # 测试渲染器创建
        from worker.app.audio_rendering import create_audio_renderer
        renderer = create_audio_renderer(renderer_type="audition")
        
        # 应该回退到默认渲染器
        assert renderer.renderer_type == "default"
        assert renderer.audition_renderer is None


class TestParameterValidation:
    """参数验证测试"""

    def test_parameter_range_validation(self):
        """测试参数范围验证"""
        converter = AuditionParameterConverter()

        # 测试EQ参数验证
        eq_params = {
            "bands": [
                {"freq": 1000, "gain": 5, "q": 1.5, "type": "peak"},
                {"freq": 50000, "gain": -30, "q": 0.01, "type": "invalid"}  # 超出范围的值
            ]
        }

        validated = converter._validate_parameter("eq", eq_params)

        # 检查频率被限制在有效范围内
        assert validated["bands"][0]["frequency"] == 1000
        assert validated["bands"][1]["frequency"] <= 20000  # 应该被限制
        assert validated["bands"][1]["gain"] >= -20  # 应该被限制
        assert validated["bands"][1]["type"] == "peak"  # 无效类型应该被修正

    def test_compression_parameter_validation(self):
        """测试压缩参数验证"""
        converter = AuditionParameterConverter()

        compression_params = {
            "threshold": -100,  # 超出范围
            "ratio": 50,       # 超出范围
            "attack": -5,      # 超出范围
            "release": 10000   # 超出范围
        }

        validated = converter._validate_parameter("compression", compression_params)

        # 检查所有参数都被限制在有效范围内
        assert -60 <= validated["threshold"] <= 0
        assert 1.0 <= validated["ratio"] <= 20.0
        assert 0.1 <= validated["attack"] <= 100
        assert 10 <= validated["release"] <= 5000

    def test_validate_style_params(self):
        """测试风格参数验证"""
        converter = AuditionParameterConverter()

        style_params = {
            "eq": {"bands": [{"freq": 1000, "gain": 5}]},
            "compression": {"threshold": -20, "ratio": 4.0},
            "unsupported": {"param": "value"}
        }

        validation = converter.validate_style_params(style_params)

        assert validation["valid"] is True
        assert len(validation["supported_params"]) == 2
        assert len(validation["unsupported_params"]) == 1
        assert "eq" in validation["supported_params"]
        assert "compression" in validation["supported_params"]
        assert "unsupported" in validation["unsupported_params"]


class TestPerformanceAndStress:
    """性能和压力测试"""

    def test_large_parameter_set_conversion(self):
        """测试大参数集转换性能"""
        converter = AuditionParameterConverter()

        # 创建大量EQ频段
        large_eq_params = {
            "eq": {
                "bands": [
                    {"freq": 100 + i * 100, "gain": (i % 10) - 5, "q": 1.0, "type": "peak"}
                    for i in range(50)  # 50个频段
                ]
            }
        }

        start_time = time.time()
        result = converter.convert_style_params(large_eq_params)
        end_time = time.time()

        # 转换应该在合理时间内完成（< 1秒）
        assert (end_time - start_time) < 1.0
        assert "eq" in result
        assert len(result["eq"]["bands"]) <= 10  # 应该被限制到最大频段数

    def test_batch_script_generation(self):
        """测试批处理脚本生成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = AuditionTemplateManager(temp_dir)

            # 创建多个文件对
            file_pairs = [
                (f"input_{i}.wav", f"output_{i}.wav")
                for i in range(5)
            ]

            audition_params = {
                "eq": {"bands": [{"freq": 1000, "gain": 3}]},
                "compression": {"threshold": -20, "ratio": 4.0}
            }

            batch_script = manager.create_batch_script(file_pairs, audition_params)

            assert os.path.exists(batch_script)
            assert batch_script.endswith('.jsx')

            # 检查脚本内容
            with open(batch_script, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "batchFiles" in content
                assert "processBatch" in content
                assert str(len(file_pairs)) in content


if __name__ == "__main__":
    pytest.main([__file__])
