"""
Adobe Audition集成配置管理
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from src.core.config import config

logger = logging.getLogger(__name__)


@dataclass
class AuditionConfig:
    """Adobe Audition配置"""
    enabled: bool = False
    executable_path: Optional[str] = None
    timeout_seconds: int = 300
    use_script_mode: bool = True
    template_directory: Optional[str] = None
    fallback_to_default: bool = True
    max_file_size_mb: float = 500.0
    
    # 性能配置
    parallel_processing: bool = False
    memory_limit_mb: float = 1024.0
    
    # 质量配置
    output_format: str = "wav"
    output_bit_depth: int = 24
    output_sample_rate: Optional[int] = None  # None表示保持原始采样率


class AuditionConfigManager:
    """Adobe Audition配置管理器（支持热重载）"""

    def __init__(self, config_file: Optional[str] = None, enable_hot_reload: bool = True):
        self.config_file = config_file or self._get_default_config_file()
        self._config = AuditionConfig()
        self.enable_hot_reload = enable_hot_reload

        # 配置变更回调
        self._change_callbacks = []

        # 加载配置
        self.load_config()

        # 初始化热重载
        if self.enable_hot_reload:
            self._setup_hot_reload()
    
    def _get_default_config_file(self) -> str:
        """获取默认配置文件路径"""
        if config.app_mode.value == "desktop":
            # 桌面版使用本地配置文件
            config_dir = Path.home() / ".audio_tuner"
            config_dir.mkdir(exist_ok=True)
            return str(config_dir / "audition_config.json")
        else:
            # 云端版使用项目配置目录
            return os.path.join(os.path.dirname(__file__), "..", "..", "config", "audition_config.json")
    
    def load_config(self) -> AuditionConfig:
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    # 更新配置对象
                    for key, value in config_data.items():
                        if hasattr(self._config, key):
                            setattr(self._config, key, value)
        except Exception as e:
            print(f"加载Adobe Audition配置失败: {e}")
        
        return self._config
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存Adobe Audition配置失败: {e}")
            return False
    
    @property
    def config(self) -> AuditionConfig:
        """获取配置对象"""
        return self._config
    
    def update_config(self, **kwargs) -> bool:
        """更新配置（支持热重载）"""
        if self.enable_hot_reload:
            try:
                from worker.app.config_hot_reload import global_config_manager
                global_config_manager.update_config("audition_config", kwargs)
                return True
            except Exception as e:
                logger.error(f"热重载更新配置失败: {e}")
                # 回退到传统方式
                return self._update_config_traditional(**kwargs)
        else:
            return self._update_config_traditional(**kwargs)

    def _update_config_traditional(self, **kwargs) -> bool:
        """传统方式更新配置"""
        try:
            old_config = AuditionConfig(**asdict(self._config))

            # 更新配置
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)

            # 保存配置
            success = self.save_config()

            # 调用回调
            if success:
                for callback in self._change_callbacks:
                    try:
                        callback(old_config, self._config)
                    except Exception as e:
                        logger.error(f"配置变更回调执行失败: {e}")

            return success
        except Exception as e:
            logger.error(f"更新Adobe Audition配置失败: {e}")
            return False
    
    def auto_detect_audition(self) -> bool:
        """自动检测Adobe Audition安装"""
        try:
            from worker.app.audition_integration import AuditionDetector
            
            detector = AuditionDetector()
            if detector.detect_installation():
                self.update_config(
                    enabled=True,
                    executable_path=detector.executable_path
                )
                return True
            else:
                self.update_config(enabled=False)
                return False
        except ImportError:
            print("Adobe Audition集成模块不可用")
            return False
        except Exception as e:
            print(f"自动检测Adobe Audition失败: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """验证配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 检查可执行文件路径
        if self._config.enabled:
            if not self._config.executable_path:
                validation_result["errors"].append("Adobe Audition可执行文件路径未设置")
                validation_result["valid"] = False
            elif not os.path.exists(self._config.executable_path):
                validation_result["errors"].append(f"Adobe Audition可执行文件不存在: {self._config.executable_path}")
                validation_result["valid"] = False
        
        # 检查模板目录
        if self._config.template_directory:
            if not os.path.exists(self._config.template_directory):
                validation_result["warnings"].append(f"模板目录不存在: {self._config.template_directory}")
        
        # 检查超时设置
        if self._config.timeout_seconds < 30:
            validation_result["warnings"].append("超时时间过短，可能导致处理失败")
        elif self._config.timeout_seconds > 1800:
            validation_result["warnings"].append("超时时间过长，可能影响用户体验")
        
        # 检查文件大小限制
        if self._config.max_file_size_mb > 1000:
            validation_result["warnings"].append("文件大小限制过大，可能导致性能问题")
        
        return validation_result
    
    def get_renderer_config(self) -> Dict[str, Any]:
        """获取渲染器配置"""
        return {
            "renderer_type": "audition" if self._config.enabled else "default",
            "audition_path": self._config.executable_path,
            "timeout": self._config.timeout_seconds,
            "temp_dir": self._config.template_directory
        }
    
    def is_file_supported(self, file_path: str) -> bool:
        """检查文件是否支持Adobe Audition处理"""
        if not self._config.enabled:
            return False
        
        # 检查文件大小
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self._config.max_file_size_mb:
                return False
        except OSError:
            return False
        
        # 检查文件格式
        supported_formats = ['.wav', '.mp3', '.flac', '.aiff', '.m4a']
        file_ext = Path(file_path).suffix.lower()
        return file_ext in supported_formats

    def _setup_hot_reload(self):
        """设置热重载"""
        try:
            # 延迟导入避免循环依赖
            from worker.app.config_hot_reload import global_config_manager

            # 注册配置文件
            global_config_manager.register_config(
                config_name="audition_config",
                config_file_path=self.config_file,
                default_config=asdict(AuditionConfig()),
                validation_callback=self._validate_config,
                change_callback=self._on_config_changed
            )

            # 启动监控
            global_config_manager.start_monitoring()

            logger.info("Adobe Audition配置热重载已启用")

        except Exception as e:
            logger.warning(f"配置热重载设置失败: {e}")
            self.enable_hot_reload = False

    def _validate_config(self, config_data: Dict[str, Any]) -> bool:
        """验证配置数据"""
        try:
            # 检查必需字段
            required_fields = ["executable_path", "timeout_seconds", "template_directory"]
            for field in required_fields:
                if field not in config_data:
                    raise ValueError(f"缺少必需字段: {field}")

            # 检查数据类型
            if not isinstance(config_data.get("timeout_seconds"), (int, float)):
                raise ValueError("timeout_seconds必须是数字")

            if config_data.get("timeout_seconds", 0) <= 0:
                raise ValueError("timeout_seconds必须大于0")

            # 检查路径
            executable_path = config_data.get("executable_path")
            if executable_path and not isinstance(executable_path, str):
                raise ValueError("executable_path必须是字符串")

            logger.debug("配置验证通过")
            return True

        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            raise

    def _on_config_changed(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """配置变更回调"""
        try:
            # 更新内部配置对象
            old_config_obj = self._config
            new_config_obj = AuditionConfig()

            # 应用新配置
            for key, value in new_config.items():
                if hasattr(new_config_obj, key):
                    setattr(new_config_obj, key, value)

            self._config = new_config_obj

            # 调用注册的回调函数
            for callback in self._change_callbacks:
                try:
                    callback(old_config_obj, new_config_obj)
                except Exception as e:
                    logger.error(f"配置变更回调执行失败: {e}")

            logger.info("Adobe Audition配置已热重载")

        except Exception as e:
            logger.error(f"配置变更处理失败: {e}")

    def register_change_callback(self, callback: Callable[[AuditionConfig, AuditionConfig], None]):
        """注册配置变更回调"""
        self._change_callbacks.append(callback)
        logger.debug("配置变更回调已注册")

    def get_hot_reload_status(self) -> Dict[str, Any]:
        """获取热重载状态"""
        status = {
            "enabled": self.enable_hot_reload,
            "config_file": self.config_file,
            "callbacks_count": len(self._change_callbacks)
        }

        if self.enable_hot_reload:
            try:
                from worker.app.config_hot_reload import global_config_manager
                reload_status = global_config_manager.get_status()
                status["reload_manager"] = reload_status
            except Exception as e:
                status["reload_manager_error"] = str(e)

        return status


# 全局配置管理器实例
audition_config_manager = AuditionConfigManager()


def get_audition_config() -> AuditionConfig:
    """获取Adobe Audition配置"""
    return audition_config_manager.config


def update_audition_config(**kwargs) -> bool:
    """更新Adobe Audition配置"""
    return audition_config_manager.update_config(**kwargs)


def validate_audition_config() -> Dict[str, Any]:
    """验证Adobe Audition配置"""
    return audition_config_manager.validate_config()


def auto_detect_audition() -> bool:
    """自动检测Adobe Audition"""
    return audition_config_manager.auto_detect_audition()


# 导出
__all__ = [
    'AuditionConfig',
    'AuditionConfigManager',
    'audition_config_manager',
    'get_audition_config',
    'update_audition_config',
    'validate_audition_config',
    'auto_detect_audition'
]
