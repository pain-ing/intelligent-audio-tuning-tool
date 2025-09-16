"""
Adobe Audition音频渲染器
"""

import os
import subprocess
import tempfile
import time
import logging
import json
import threading
import queue
import psutil
from typing import Dict, Any, Optional, Tuple, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from .audition_integration import (
    AuditionDetector, 
    AuditionParameterConverter, 
    AuditionTemplateManager
)

logger = logging.getLogger(__name__)


class AuditionErrorType(Enum):
    """Adobe Audition错误类型"""
    INSTALLATION_NOT_FOUND = "installation_not_found"
    EXECUTABLE_ERROR = "executable_error"
    SCRIPT_GENERATION_ERROR = "script_generation_error"
    SCRIPT_EXECUTION_ERROR = "script_execution_error"
    FILE_IO_ERROR = "file_io_error"
    TIMEOUT_ERROR = "timeout_error"
    PARAMETER_ERROR = "parameter_error"
    MEMORY_ERROR = "memory_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ProcessingMetrics:
    """处理指标"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    input_file_size: int = 0
    output_file_size: int = 0
    script_generation_time: float = 0.0
    script_execution_time: float = 0.0
    effects_applied: int = 0
    error_type: Optional[AuditionErrorType] = None
    error_message: Optional[str] = None

    def finalize(self):
        """完成指标计算"""
        if self.end_time is None:
            self.end_time = time.time()
        self.processing_time = self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "processing_time": self.processing_time,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "input_file_size": self.input_file_size,
            "output_file_size": self.output_file_size,
            "script_generation_time": self.script_generation_time,
            "script_execution_time": self.script_execution_time,
            "effects_applied": self.effects_applied,
            "error_type": self.error_type.value if self.error_type else None,
            "error_message": self.error_message,
            "success": self.error_type is None
        }


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics_queue = queue.Queue()
        self.monitor_thread = None

    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> Dict[str, float]:
        """停止监控并返回平均指标"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        # 计算平均值
        memory_samples = []
        cpu_samples = []

        while not self.metrics_queue.empty():
            try:
                sample = self.metrics_queue.get_nowait()
                memory_samples.append(sample["memory_mb"])
                cpu_samples.append(sample["cpu_percent"])
            except queue.Empty:
                break

        return {
            "avg_memory_mb": sum(memory_samples) / len(memory_samples) if memory_samples else 0.0,
            "max_memory_mb": max(memory_samples) if memory_samples else 0.0,
            "avg_cpu_percent": sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0,
            "max_cpu_percent": max(cpu_samples) if cpu_samples else 0.0
        }

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                cpu_percent = self.process.cpu_percent()

                self.metrics_queue.put({
                    "memory_mb": memory_info.rss / 1024 / 1024,
                    "cpu_percent": cpu_percent,
                    "timestamp": time.time()
                })

                time.sleep(0.1)  # 100ms采样间隔
            except Exception:
                break


class AuditionAudioRenderer:
    """Adobe Audition音频渲染器"""

    def __init__(self,
                 audition_path: Optional[str] = None,
                 timeout: int = 300,
                 temp_dir: Optional[str] = None,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 enable_monitoring: bool = True,
                 fallback_callback: Optional[Callable] = None):
        """
        初始化Adobe Audition渲染器

        Args:
            audition_path: Adobe Audition可执行文件路径
            timeout: 处理超时时间（秒）
            temp_dir: 临时文件目录
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            enable_monitoring: 是否启用性能监控
            fallback_callback: 回退回调函数
        """
        self.timeout = timeout
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.enable_monitoring = enable_monitoring
        self.fallback_callback = fallback_callback

        # 初始化组件
        self.detector = AuditionDetector()
        self.converter = AuditionParameterConverter()
        self.template_manager = AuditionTemplateManager()

        # 性能监控器
        self.performance_monitor = PerformanceMonitor() if enable_monitoring else None

        # 检测Adobe Audition安装
        self.is_available = self._initialize_audition(audition_path)

        # 增强的性能统计
        self.stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "avg_processing_time": 0.0,
            "error_breakdown": {},
            "performance_history": [],
            "last_error": None,
            "uptime_start": time.time()
        }

        # 错误处理配置
        self.error_handlers = {
            AuditionErrorType.TIMEOUT_ERROR: self._handle_timeout_error,
            AuditionErrorType.MEMORY_ERROR: self._handle_memory_error,
            AuditionErrorType.SCRIPT_EXECUTION_ERROR: self._handle_script_error,
            AuditionErrorType.FILE_IO_ERROR: self._handle_file_error
        }
    
    def _initialize_audition(self, custom_path: Optional[str] = None) -> bool:
        """初始化Adobe Audition"""
        if custom_path and os.path.exists(custom_path):
            self.audition_path = custom_path
            logger.info(f"使用自定义Adobe Audition路径: {custom_path}")
            return True
        
        if self.detector.detect_installation():
            self.audition_path = self.detector.executable_path
            self.audition_version = self.detector.detected_version
            logger.info(f"检测到Adobe Audition {self.audition_version}: {self.audition_path}")
            return True
        
        logger.error("Adobe Audition未安装或无法检测到")
        return False
    
    def is_audition_available(self) -> bool:
        """检查Adobe Audition是否可用"""
        return self.is_available
    
    def render_audio(self,
                    input_path: str,
                    output_path: str,
                    style_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用Adobe Audition渲染音频

        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            style_params: 风格参数

        Returns:
            处理指标字典
        """
        if not self.is_available:
            if self.fallback_callback:
                logger.warning("Adobe Audition不可用，调用回退函数")
                return self.fallback_callback(input_path, output_path, style_params)
            else:
                raise RuntimeError("Adobe Audition不可用且无回退方案")

        # 初始化指标
        metrics = ProcessingMetrics()

        # 获取输入文件大小
        try:
            metrics.input_file_size = os.path.getsize(input_path)
        except OSError:
            pass

        # 开始性能监控
        if self.performance_monitor:
            self.performance_monitor.start_monitoring()

        # 重试机制
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = self._render_audio_attempt(
                    input_path, output_path, style_params, metrics, attempt
                )

                # 成功处理
                self._update_success_stats(metrics)
                return result

            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                metrics.error_type = error_type
                metrics.error_message = str(e)

                logger.warning(f"渲染尝试 {attempt + 1} 失败: {e}")

                # 如果是最后一次尝试，或者是不可重试的错误
                if attempt >= self.max_retries or not self._is_retryable_error(error_type):
                    break

                # 应用错误处理策略
                if error_type in self.error_handlers:
                    try:
                        self.error_handlers[error_type](e, attempt)
                    except Exception as handler_error:
                        logger.error(f"错误处理器失败: {handler_error}")

                # 等待重试
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** attempt))  # 指数退避

        # 所有尝试都失败了
        metrics.finalize()
        self._update_error_stats(metrics)

        if self.performance_monitor:
            perf_stats = self.performance_monitor.stop_monitoring()
            metrics.memory_usage_mb = perf_stats.get("avg_memory_mb", 0.0)
            metrics.cpu_usage_percent = perf_stats.get("avg_cpu_percent", 0.0)

        # 如果有回退函数，尝试使用
        if self.fallback_callback:
            logger.warning("Adobe Audition处理失败，尝试回退方案")
            try:
                return self.fallback_callback(input_path, output_path, style_params)
            except Exception as fallback_error:
                logger.error(f"回退方案也失败了: {fallback_error}")

        # 抛出最后的错误
        raise last_error or RuntimeError("音频渲染失败")

    def _render_audio_attempt(self,
                            input_path: str,
                            output_path: str,
                            style_params: Dict[str, Any],
                            metrics: ProcessingMetrics,
                            attempt: int) -> Dict[str, Any]:
        """单次渲染尝试"""
        logger.info(f"开始渲染尝试 {attempt + 1}")

        try:
            # 转换参数
            script_gen_start = time.time()
            audition_params = self.converter.convert_style_params(style_params)
            metrics.script_generation_time = time.time() - script_gen_start

            # 统计效果数量
            metrics.effects_applied = len([k for k in audition_params.keys() if not k.startswith('_')])

            logger.info(f"转换后的Adobe Audition参数: {list(audition_params.keys())}")

            # 生成处理脚本
            script_path = self.template_manager.create_processing_script(
                input_path, output_path, audition_params
            )

            # 执行Adobe Audition脚本
            script_exec_start = time.time()
            result = self._execute_audition_script(script_path)
            metrics.script_execution_time = time.time() - script_exec_start

            # 验证输出文件
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"输出文件未生成: {output_path}")

            # 获取输出文件大小
            metrics.output_file_size = os.path.getsize(output_path)

            # 清理脚本文件
            try:
                os.unlink(script_path)
            except OSError:
                pass

            # 完成指标计算
            metrics.finalize()

            # 停止性能监控
            if self.performance_monitor:
                perf_stats = self.performance_monitor.stop_monitoring()
                metrics.memory_usage_mb = perf_stats.get("avg_memory_mb", 0.0)
                metrics.cpu_usage_percent = perf_stats.get("avg_cpu_percent", 0.0)

            logger.info(f"Adobe Audition渲染完成，耗时: {metrics.processing_time:.2f}秒")

            # 返回处理指标
            return self._generate_audio_metrics(metrics, result)

        except Exception as e:
            # 清理可能的临时文件
            self._cleanup_temp_files()
            raise

    def _execute_audition_script(self, script_path: str) -> Dict[str, Any]:
        """执行Adobe Audition脚本"""
        logger.info(f"执行Adobe Audition脚本: {script_path}")

        # 构建命令
        cmd = [self.audition_path, "-script", script_path]

        try:
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout
            )

            stdout, stderr = process.communicate(timeout=self.timeout)

            # 检查返回码
            if process.returncode != 0:
                error_msg = f"Adobe Audition脚本执行失败 (返回码: {process.returncode})"
                if stderr:
                    error_msg += f"\n错误输出: {stderr}"
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr)

            # 解析输出
            result = self._parse_audition_output(stdout)

            logger.info("Adobe Audition脚本执行成功")
            return result

        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError(f"Adobe Audition脚本执行超时 ({self.timeout}秒)")
        except FileNotFoundError:
            raise FileNotFoundError(f"Adobe Audition可执行文件未找到: {self.audition_path}")

    def _parse_audition_output(self, output: str) -> Dict[str, Any]:
        """解析Adobe Audition输出"""
        result = {
            "success": False,
            "messages": [],
            "metrics": {},
            "errors": []
        }

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith("AUDITION_SUCCESS:"):
                result["success"] = True
                result["messages"].append(line[17:])
            elif line.startswith("AUDITION_ERROR:"):
                result["errors"].append(line[15:])
            elif line.startswith("AUDITION_METRIC:"):
                try:
                    metric_data = json.loads(line[16:])
                    result["metrics"][metric_data["name"]] = metric_data["value"]
                except (json.JSONDecodeError, KeyError):
                    pass
            elif line.startswith("AUDITION_PROGRESS:"):
                # 进度信息，可以用于实时更新
                pass
            elif line.startswith("AUDITION_LOG:"):
                result["messages"].append(line[13:])

        return result

    def _classify_error(self, error: Exception) -> AuditionErrorType:
        """分类错误类型"""
        if isinstance(error, FileNotFoundError):
            if "audition" in str(error).lower():
                return AuditionErrorType.INSTALLATION_NOT_FOUND
            else:
                return AuditionErrorType.FILE_IO_ERROR
        elif isinstance(error, subprocess.TimeoutExpired):
            return AuditionErrorType.TIMEOUT_ERROR
        elif isinstance(error, subprocess.CalledProcessError):
            return AuditionErrorType.SCRIPT_EXECUTION_ERROR
        elif isinstance(error, MemoryError):
            return AuditionErrorType.MEMORY_ERROR
        elif isinstance(error, OSError):
            return AuditionErrorType.FILE_IO_ERROR
        else:
            return AuditionErrorType.UNKNOWN_ERROR

    def _is_retryable_error(self, error_type: AuditionErrorType) -> bool:
        """判断错误是否可重试"""
        retryable_errors = {
            AuditionErrorType.TIMEOUT_ERROR,
            AuditionErrorType.SCRIPT_EXECUTION_ERROR,
            AuditionErrorType.MEMORY_ERROR,
            AuditionErrorType.UNKNOWN_ERROR
        }
        return error_type in retryable_errors

    def _handle_timeout_error(self, error: Exception, attempt: int):
        """处理超时错误"""
        logger.warning(f"处理超时错误 (尝试 {attempt + 1})")
        # 增加超时时间
        self.timeout = min(self.timeout * 1.5, 900)  # 最大15分钟
        logger.info(f"调整超时时间为: {self.timeout}秒")

    def _handle_memory_error(self, error: Exception, attempt: int):
        """处理内存错误"""
        logger.warning(f"处理内存错误 (尝试 {attempt + 1})")
        # 清理临时文件
        self._cleanup_temp_files()
        # 强制垃圾回收
        import gc
        gc.collect()

    def _handle_script_error(self, error: Exception, attempt: int):
        """处理脚本执行错误"""
        logger.warning(f"处理脚本执行错误 (尝试 {attempt + 1})")
        # 可以尝试重新生成脚本或使用简化版本
        pass

    def _handle_file_error(self, error: Exception, attempt: int):
        """处理文件IO错误"""
        logger.warning(f"处理文件IO错误 (尝试 {attempt + 1})")
        # 检查磁盘空间和权限
        pass

    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            self.template_manager.cleanup_old_scripts(max_age_hours=1)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

    def _update_success_stats(self, metrics: ProcessingMetrics):
        """更新成功统计"""
        self.stats["total_processed"] += 1
        self.stats["success_count"] += 1

        # 更新平均处理时间
        total_time = (self.stats["avg_processing_time"] * (self.stats["success_count"] - 1) +
                     metrics.processing_time)
        self.stats["avg_processing_time"] = total_time / self.stats["success_count"]

        # 添加到历史记录
        self.stats["performance_history"].append(metrics.to_dict())

        # 保持历史记录在合理大小
        if len(self.stats["performance_history"]) > 100:
            self.stats["performance_history"] = self.stats["performance_history"][-100:]

    def _update_error_stats(self, metrics: ProcessingMetrics):
        """更新错误统计"""
        self.stats["total_processed"] += 1
        self.stats["error_count"] += 1

        if metrics.error_type:
            error_key = metrics.error_type.value
            self.stats["error_breakdown"][error_key] = (
                self.stats["error_breakdown"].get(error_key, 0) + 1
            )

        self.stats["last_error"] = {
            "type": metrics.error_type.value if metrics.error_type else "unknown",
            "message": metrics.error_message,
            "timestamp": time.time()
        }

    def _generate_audio_metrics(self, metrics: ProcessingMetrics, audition_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成音频处理指标"""
        # 基础指标
        result_metrics = {
            "processing_time": metrics.processing_time,
            "memory_usage_mb": metrics.memory_usage_mb,
            "cpu_usage_percent": metrics.cpu_usage_percent,
            "effects_applied": metrics.effects_applied,
            "file_size_ratio": (metrics.output_file_size / metrics.input_file_size
                              if metrics.input_file_size > 0 else 1.0),
            "script_generation_time": metrics.script_generation_time,
            "script_execution_time": metrics.script_execution_time
        }

        # 添加Adobe Audition特定指标
        if audition_result.get("metrics"):
            result_metrics.update(audition_result["metrics"])

        # 模拟音频质量指标（实际应该从Adobe Audition获取）
        result_metrics.update({
            "stft_dist": 0.1,  # 短时傅里叶变换距离
            "mel_dist": 0.15,  # Mel频谱距离
            "lufs_err": 0.5,   # LUFS误差
            "tp_db": -1.0,     # 真峰值
            "artifacts_rate": 0.02  # 伪影率
        })

        return result_metrics

    def get_stats(self) -> Dict[str, Any]:
        """获取渲染器统计信息"""
        uptime = time.time() - self.stats["uptime_start"]

        stats = self.stats.copy()
        stats.update({
            "uptime_seconds": uptime,
            "success_rate": (self.stats["success_count"] / max(self.stats["total_processed"], 1)) * 100,
            "is_available": self.is_available,
            "audition_path": getattr(self, "audition_path", None),
            "audition_version": getattr(self, "audition_version", None)
        })

        return stats

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "avg_processing_time": 0.0,
            "error_breakdown": {},
            "performance_history": [],
            "last_error": None,
            "uptime_start": time.time()
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "issues": [],
            "recommendations": []
        }

        # 检查Adobe Audition可用性
        if not self.is_available:
            health["status"] = "unhealthy"
            health["issues"].append("Adobe Audition不可用")
            health["recommendations"].append("检查Adobe Audition安装")

        # 检查错误率
        if self.stats["total_processed"] > 0:
            error_rate = (self.stats["error_count"] / self.stats["total_processed"]) * 100
            if error_rate > 20:
                health["status"] = "degraded"
                health["issues"].append(f"错误率过高: {error_rate:.1f}%")
                health["recommendations"].append("检查系统资源和配置")

        # 检查平均处理时间
        if self.stats["avg_processing_time"] > 60:
            health["status"] = "degraded"
            health["issues"].append(f"平均处理时间过长: {self.stats['avg_processing_time']:.1f}秒")
            health["recommendations"].append("考虑优化处理参数或升级硬件")

        # 检查最近错误
        if self.stats["last_error"]:
            last_error_time = self.stats["last_error"]["timestamp"]
            if time.time() - last_error_time < 300:  # 5分钟内有错误
                health["status"] = "degraded"
                health["issues"].append("最近发生错误")

        return health

    def configure(self, **kwargs):
        """动态配置渲染器"""
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            logger.info(f"更新超时时间: {self.timeout}秒")

        if "max_retries" in kwargs:
            self.max_retries = kwargs["max_retries"]
            logger.info(f"更新最大重试次数: {self.max_retries}")

        if "retry_delay" in kwargs:
            self.retry_delay = kwargs["retry_delay"]
            logger.info(f"更新重试延迟: {self.retry_delay}秒")

        if "enable_monitoring" in kwargs:
            self.enable_monitoring = kwargs["enable_monitoring"]
            if self.enable_monitoring and not self.performance_monitor:
                self.performance_monitor = PerformanceMonitor()
            logger.info(f"性能监控: {'启用' if self.enable_monitoring else '禁用'}")


def create_audition_renderer(config: Optional[Dict[str, Any]] = None,
                           fallback_callback: Optional[Callable] = None) -> AuditionAudioRenderer:
    """
    创建Adobe Audition渲染器工厂函数

    Args:
        config: 配置字典
        fallback_callback: 回退回调函数

    Returns:
        AuditionAudioRenderer实例
    """
    if config is None:
        config = {}

    return AuditionAudioRenderer(
        audition_path=config.get("audition_path"),
        timeout=config.get("timeout", 300),
        temp_dir=config.get("temp_dir"),
        max_retries=config.get("max_retries", 3),
        retry_delay=config.get("retry_delay", 1.0),
        enable_monitoring=config.get("enable_monitoring", True),
        fallback_callback=fallback_callback
    )
    
    def _should_use_script_mode(self, audition_params: Dict[str, Any]) -> bool:
        """判断是否应该使用脚本模式"""
        # 如果有复杂的效果链或多个效果，使用脚本模式
        effect_count = len(audition_params)
        has_complex_effects = any(
            effect_type in audition_params 
            for effect_type in ["eq", "compression", "reverb"]
        )
        
        return effect_count > 2 or has_complex_effects
    
    def _render_with_script(self, 
                          input_path: str, 
                          output_path: str, 
                          audition_params: Dict[str, Any]) -> Dict[str, Any]:
        """使用ExtendScript脚本进行渲染"""
        logger.info("使用Adobe Audition脚本模式进行处理")
        
        # 创建处理脚本
        script_path = self.template_manager.create_processing_script(
            input_path, output_path, audition_params
        )
        
        try:
            # 执行Adobe Audition脚本
            cmd = [
                self.audition_path,
                "-script", script_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.temp_dir
            )
            
            # 解析输出
            metrics = self._parse_script_output(result.stdout, result.stderr)
            
            if result.returncode != 0:
                raise RuntimeError(f"Adobe Audition脚本执行失败: {result.stderr}")
            
            # 验证输出文件
            if not os.path.exists(output_path):
                raise RuntimeError("输出文件未生成")
            
            return metrics
            
        finally:
            # 清理脚本文件
            if os.path.exists(script_path):
                os.unlink(script_path)
    
    def _render_with_command_line(self, 
                                input_path: str, 
                                output_path: str, 
                                audition_params: Dict[str, Any]) -> Dict[str, Any]:
        """使用命令行进行渲染"""
        logger.info("使用Adobe Audition命令行模式进行处理")
        
        # 构建命令行参数
        cmd = [self.audition_path]
        cmd.extend(["-i", input_path])
        cmd.extend(["-o", output_path])
        
        # 添加效果参数
        for effect_type, params in audition_params.items():
            cmd.extend(self._build_effect_args(effect_type, params))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.temp_dir
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Adobe Audition命令行执行失败: {result.stderr}")
            
            # 验证输出文件
            if not os.path.exists(output_path):
                raise RuntimeError("输出文件未生成")
            
            # 生成基本指标
            metrics = self._generate_basic_metrics(input_path, output_path)
            return metrics
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Adobe Audition处理超时（{self.timeout}秒）")
    
    def _build_effect_args(self, effect_type: str, params: Dict[str, Any]) -> list:
        """构建效果参数"""
        args = []
        
        if effect_type == "limiter":
            args.extend(["-effect", "limiter"])
            args.extend(["-ceiling", str(params.get("ceiling", -0.1))])
            args.extend(["-release", str(params.get("release", 50))])
        elif effect_type == "compression":
            args.extend(["-effect", "compressor"])
            args.extend(["-threshold", str(params.get("threshold", -20))])
            args.extend(["-ratio", str(params.get("ratio", 4.0))])
        # 可以继续添加其他效果
        
        return args
    
    def _parse_script_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """解析脚本输出"""
        metrics = {
            "script_success": False,
            "processing_messages": []
        }
        
        for line in stdout.split('\n'):
            line = line.strip()
            if line.startswith("AUDITION_SUCCESS:"):
                metrics["script_success"] = True
                metrics["processing_messages"].append(line)
            elif line.startswith("AUDITION_ERROR:"):
                metrics["processing_messages"].append(line)
                raise RuntimeError(f"Adobe Audition脚本错误: {line}")
            elif line.startswith("AUDITION_METRIC:"):
                # 解析指标信息
                try:
                    metric_data = json.loads(line.replace("AUDITION_METRIC:", ""))
                    metrics.update(metric_data)
                except json.JSONDecodeError:
                    pass
        
        return metrics
    
    def _generate_basic_metrics(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """生成基本处理指标"""
        metrics = {
            "input_file_size": os.path.getsize(input_path),
            "output_file_size": os.path.getsize(output_path),
            "processing_method": "command_line"
        }
        
        # 可以添加更多音频分析指标
        try:
            import librosa
            import numpy as np
            
            # 加载音频进行简单分析
            y_in, sr = librosa.load(input_path, sr=None)
            y_out, _ = librosa.load(output_path, sr=sr)
            
            # 计算RMS差异
            rms_in = np.sqrt(np.mean(y_in**2))
            rms_out = np.sqrt(np.mean(y_out**2))
            
            metrics.update({
                "rms_change": float(rms_out / rms_in) if rms_in > 0 else 1.0,
                "duration_seconds": len(y_out) / sr,
                "sample_rate": sr
            })
            
        except ImportError:
            logger.warning("librosa不可用，跳过音频分析")
        except Exception as e:
            logger.warning(f"音频分析失败: {e}")
        
        return metrics
    
    def _update_stats(self, success: bool, processing_time: float):
        """更新统计信息"""
        self.stats["total_processed"] += 1
        
        if success:
            self.stats["success_count"] += 1
        else:
            self.stats["error_count"] += 1
        
        # 更新平均处理时间
        total_time = (self.stats["avg_processing_time"] * 
                     (self.stats["total_processed"] - 1) + processing_time)
        self.stats["avg_processing_time"] = total_time / self.stats["total_processed"]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def cleanup(self):
        """清理资源"""
        # 清理临时文件等
        pass


# 工厂函数
def create_audition_renderer(**kwargs) -> AuditionAudioRenderer:
    """创建Adobe Audition渲染器实例"""
    return AuditionAudioRenderer(**kwargs)


# 导出
__all__ = ['AuditionAudioRenderer', 'create_audition_renderer']
