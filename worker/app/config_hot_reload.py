"""
配置热重载模块
支持运行时配置更新，无需重启服务
"""

import os
import json
import time
import threading
import logging
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


@dataclass
class ConfigChangeEvent:
    """配置变更事件"""
    config_name: str
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=time.time)
    change_type: str = "update"  # update, add, delete


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监控器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.last_modified = {}
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # 检查是否是配置文件
        if not self._is_config_file(file_path):
            return
        
        # 防止重复触发
        current_time = time.time()
        last_time = self.last_modified.get(file_path, 0)
        if current_time - last_time < 1.0:  # 1秒内的重复事件忽略
            return
        
        self.last_modified[file_path] = current_time
        
        logger.info(f"检测到配置文件变更: {file_path}")
        
        # 延迟重载，避免文件正在写入
        threading.Timer(0.5, self._reload_config_file, args=[file_path]).start()
    
    def _is_config_file(self, file_path: str) -> bool:
        """检查是否是配置文件"""
        config_extensions = ['.json', '.yaml', '.yml', '.toml', '.ini']
        return any(file_path.endswith(ext) for ext in config_extensions)
    
    def _reload_config_file(self, file_path: str):
        """重载配置文件"""
        try:
            self.config_manager.reload_config_file(file_path)
        except Exception as e:
            logger.error(f"重载配置文件失败 {file_path}: {e}")


class ConfigHotReloadManager:
    """配置热重载管理器"""
    
    def __init__(self):
        self.configs = {}
        self.config_files = {}
        self.change_callbacks = {}
        self.validation_callbacks = {}
        self.observer = None
        self.watcher = None
        self.monitoring = False
        self._lock = threading.Lock()
        
        # 变更历史
        self.change_history = []
        self.max_history_size = 100
    
    def register_config(self, 
                       config_name: str, 
                       config_file_path: str,
                       default_config: Dict[str, Any] = None,
                       validation_callback: Optional[Callable] = None,
                       change_callback: Optional[Callable] = None):
        """
        注册配置文件
        
        Args:
            config_name: 配置名称
            config_file_path: 配置文件路径
            default_config: 默认配置
            validation_callback: 配置验证回调函数
            change_callback: 配置变更回调函数
        """
        with self._lock:
            # 加载初始配置
            config = self._load_config_file(config_file_path, default_config)
            
            self.configs[config_name] = config
            self.config_files[config_name] = config_file_path
            
            if validation_callback:
                self.validation_callbacks[config_name] = validation_callback
            
            if change_callback:
                self.change_callbacks[config_name] = change_callback
            
            logger.info(f"注册配置: {config_name} -> {config_file_path}")
    
    def start_monitoring(self):
        """开始监控配置文件变更"""
        if self.monitoring:
            return
        
        self.watcher = ConfigFileWatcher(self)
        self.observer = Observer()
        
        # 监控所有配置文件的目录
        monitored_dirs = set()
        for config_file in self.config_files.values():
            config_dir = os.path.dirname(os.path.abspath(config_file))
            if config_dir not in monitored_dirs:
                self.observer.schedule(self.watcher, config_dir, recursive=False)
                monitored_dirs.add(config_dir)
                logger.info(f"监控配置目录: {config_dir}")
        
        self.observer.start()
        self.monitoring = True
        logger.info("配置热重载监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.monitoring:
            return
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.monitoring = False
        logger.info("配置热重载监控已停止")
    
    def get_config(self, config_name: str) -> Dict[str, Any]:
        """获取配置"""
        with self._lock:
            return self.configs.get(config_name, {}).copy()
    
    def update_config(self, config_name: str, updates: Dict[str, Any], save_to_file: bool = True):
        """
        更新配置
        
        Args:
            config_name: 配置名称
            updates: 更新的配置项
            save_to_file: 是否保存到文件
        """
        with self._lock:
            if config_name not in self.configs:
                raise ValueError(f"未注册的配置: {config_name}")
            
            old_config = self.configs[config_name].copy()
            new_config = old_config.copy()
            
            # 应用更新
            self._deep_update(new_config, updates)
            
            # 验证配置
            if config_name in self.validation_callbacks:
                try:
                    self.validation_callbacks[config_name](new_config)
                except Exception as e:
                    logger.error(f"配置验证失败 {config_name}: {e}")
                    raise
            
            # 更新配置
            self.configs[config_name] = new_config
            
            # 记录变更
            for key, new_value in updates.items():
                old_value = self._get_nested_value(old_config, key)
                change_event = ConfigChangeEvent(
                    config_name=f"{config_name}.{key}",
                    old_value=old_value,
                    new_value=new_value
                )
                self._add_change_event(change_event)
            
            # 保存到文件
            if save_to_file and config_name in self.config_files:
                self._save_config_file(self.config_files[config_name], new_config)
            
            # 调用变更回调
            if config_name in self.change_callbacks:
                try:
                    self.change_callbacks[config_name](old_config, new_config)
                except Exception as e:
                    logger.error(f"配置变更回调执行失败 {config_name}: {e}")
            
            logger.info(f"配置已更新: {config_name}")
    
    def reload_config_file(self, file_path: str):
        """重载配置文件"""
        with self._lock:
            # 找到对应的配置名称
            config_name = None
            for name, path in self.config_files.items():
                if os.path.abspath(path) == os.path.abspath(file_path):
                    config_name = name
                    break
            
            if not config_name:
                logger.warning(f"未找到对应的配置: {file_path}")
                return
            
            try:
                # 加载新配置
                old_config = self.configs[config_name].copy()
                new_config = self._load_config_file(file_path)
                
                # 验证配置
                if config_name in self.validation_callbacks:
                    self.validation_callbacks[config_name](new_config)
                
                # 更新配置
                self.configs[config_name] = new_config
                
                # 记录变更
                changes = self._find_config_changes(old_config, new_config)
                for change in changes:
                    change.config_name = f"{config_name}.{change.config_name}"
                    self._add_change_event(change)
                
                # 调用变更回调
                if config_name in self.change_callbacks:
                    self.change_callbacks[config_name](old_config, new_config)
                
                logger.info(f"配置文件已重载: {config_name}")
                
            except Exception as e:
                logger.error(f"重载配置文件失败 {file_path}: {e}")
                raise
    
    def _load_config_file(self, file_path: str, default_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(file_path):
            if default_config:
                logger.info(f"配置文件不存在，使用默认配置: {file_path}")
                return default_config.copy()
            else:
                raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    config = json.load(f)
                else:
                    # 其他格式的支持可以在这里添加
                    raise ValueError(f"不支持的配置文件格式: {file_path}")
            
            return config
            
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            if default_config:
                logger.info("使用默认配置")
                return default_config.copy()
            raise
    
    def _save_config_file(self, file_path: str, config: Dict[str, Any]):
        """保存配置文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"不支持的配置文件格式: {file_path}")
            
            logger.debug(f"配置文件已保存: {file_path}")
            
        except Exception as e:
            logger.error(f"保存配置文件失败 {file_path}: {e}")
            raise
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]):
        """深度更新字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """获取嵌套键值"""
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return value
    
    def _find_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> List[ConfigChangeEvent]:
        """查找配置变更"""
        changes = []
        
        def compare_dicts(old_dict, new_dict, prefix=""):
            # 检查新增和修改
            for key, new_value in new_dict.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if key not in old_dict:
                    # 新增
                    changes.append(ConfigChangeEvent(
                        config_name=full_key,
                        old_value=None,
                        new_value=new_value,
                        change_type="add"
                    ))
                elif old_dict[key] != new_value:
                    if isinstance(old_dict[key], dict) and isinstance(new_value, dict):
                        # 递归比较嵌套字典
                        compare_dicts(old_dict[key], new_value, full_key)
                    else:
                        # 修改
                        changes.append(ConfigChangeEvent(
                            config_name=full_key,
                            old_value=old_dict[key],
                            new_value=new_value,
                            change_type="update"
                        ))
            
            # 检查删除
            for key, old_value in old_dict.items():
                if key not in new_dict:
                    full_key = f"{prefix}.{key}" if prefix else key
                    changes.append(ConfigChangeEvent(
                        config_name=full_key,
                        old_value=old_value,
                        new_value=None,
                        change_type="delete"
                    ))
        
        compare_dicts(old_config, new_config)
        return changes
    
    def _add_change_event(self, event: ConfigChangeEvent):
        """添加变更事件到历史"""
        self.change_history.append(event)
        
        # 限制历史大小
        if len(self.change_history) > self.max_history_size:
            self.change_history = self.change_history[-self.max_history_size:]
    
    def get_change_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取变更历史"""
        recent_changes = self.change_history[-limit:]
        return [
            {
                "config_name": event.config_name,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "timestamp": event.timestamp,
                "change_type": event.change_type
            }
            for event in recent_changes
        ]
    
    def get_status(self) -> Dict[str, Any]:
        """获取热重载状态"""
        return {
            "monitoring": self.monitoring,
            "registered_configs": list(self.configs.keys()),
            "config_files": self.config_files.copy(),
            "change_history_count": len(self.change_history),
            "callbacks_registered": {
                "validation": list(self.validation_callbacks.keys()),
                "change": list(self.change_callbacks.keys())
            }
        }


# 全局配置热重载管理器
global_config_manager = ConfigHotReloadManager()
global_hot_reload_manager = global_config_manager  # 别名
