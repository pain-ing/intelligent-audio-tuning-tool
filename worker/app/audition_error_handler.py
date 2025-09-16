"""
Adobe Audition集成高级错误处理模块
"""

import os
import time
import logging
import traceback
import threading
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """恢复策略"""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    DEGRADE = "degrade"
    CIRCUIT_BREAKER = "circuit_breaker"


@dataclass
class ErrorContext:
    """错误上下文"""
    error_type: str
    error_message: str
    timestamp: float = field(default_factory=time.time)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.RETRY
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    attempt_count: int = 0
    max_attempts: int = 3
    
    def __post_init__(self):
        if self.stack_trace is None:
            self.stack_trace = traceback.format_exc()


class CircuitBreaker:
    """熔断器模式实现"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs):
        """调用函数，应用熔断器逻辑"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("熔断器开启，拒绝调用")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ErrorAnalyzer:
    """错误分析器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.error_history = deque(maxlen=window_size)
        self.error_patterns = defaultdict(int)
        self.error_trends = defaultdict(list)
    
    def analyze_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """分析错误"""
        self.error_history.append(error_context)
        self.error_patterns[error_context.error_type] += 1
        
        # 分析错误趋势
        current_time = time.time()
        self.error_trends[error_context.error_type].append(current_time)
        
        # 清理旧的趋势数据（保留最近1小时）
        cutoff_time = current_time - 3600
        for error_type in self.error_trends:
            self.error_trends[error_type] = [
                t for t in self.error_trends[error_type] if t > cutoff_time
            ]
        
        return {
            "error_frequency": self.error_patterns[error_context.error_type],
            "recent_errors": len([e for e in self.error_history 
                                if e.timestamp > current_time - 300]),  # 最近5分钟
            "error_rate": self._calculate_error_rate(error_context.error_type),
            "recommended_action": self._recommend_action(error_context)
        }
    
    def _calculate_error_rate(self, error_type: str) -> float:
        """计算错误率"""
        recent_errors = self.error_trends[error_type]
        if len(recent_errors) < 2:
            return 0.0
        
        time_span = recent_errors[-1] - recent_errors[0]
        if time_span == 0:
            return 0.0
        
        return len(recent_errors) / time_span * 60  # 每分钟错误数
    
    def _recommend_action(self, error_context: ErrorContext) -> RecoveryStrategy:
        """推荐处理动作"""
        error_rate = self._calculate_error_rate(error_context.error_type)

        if error_rate > 10:  # 每分钟超过10个错误
            return RecoveryStrategy.CIRCUIT_BREAKER
        elif error_rate > 5:
            return RecoveryStrategy.DEGRADE
        elif error_context.attempt_count >= error_context.max_attempts:
            return RecoveryStrategy.FALLBACK
        else:
            return RecoveryStrategy.RETRY


class AuditionErrorHandler:
    """Adobe Audition错误处理器"""
    
    def __init__(self):
        self.error_analyzer = ErrorAnalyzer()
        self.circuit_breakers = {}
        self.recovery_strategies = {}
        self.error_callbacks = {}
        
        # 注册默认恢复策略
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认恢复策略"""
        self.recovery_strategies.update({
            "timeout_error": self._handle_timeout_error,
            "memory_error": self._handle_memory_error,
            "script_error": self._handle_script_error,
            "file_error": self._handle_file_error,
            "installation_error": self._handle_installation_error
        })
    
    def handle_error(self, 
                    error: Exception, 
                    error_type: str,
                    context: Dict[str, Any] = None) -> ErrorContext:
        """处理错误"""
        error_context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            metadata=context or {}
        )
        
        # 分析错误
        analysis = self.error_analyzer.analyze_error(error_context)
        error_context.metadata.update(analysis)
        
        # 确定恢复策略
        recommended_action = analysis.get("recommended_action", "RETRY")
        error_context.recovery_strategy = RecoveryStrategy(recommended_action.lower())
        
        # 应用恢复策略
        if error_type in self.recovery_strategies:
            try:
                self.recovery_strategies[error_type](error_context)
            except Exception as strategy_error:
                logger.error(f"恢复策略执行失败: {strategy_error}")
        
        # 调用错误回调
        if error_type in self.error_callbacks:
            try:
                self.error_callbacks[error_type](error_context)
            except Exception as callback_error:
                logger.error(f"错误回调执行失败: {callback_error}")
        
        return error_context
    
    def _handle_timeout_error(self, error_context: ErrorContext):
        """处理超时错误"""
        logger.warning("处理超时错误")
        
        # 增加超时时间
        current_timeout = error_context.metadata.get("timeout", 300)
        new_timeout = min(current_timeout * 1.5, 900)  # 最大15分钟
        error_context.metadata["suggested_timeout"] = new_timeout
        
        # 如果超时频繁，建议降级服务
        if error_context.metadata.get("error_rate", 0) > 5:
            error_context.recovery_strategy = RecoveryStrategy.DEGRADE
    
    def _handle_memory_error(self, error_context: ErrorContext):
        """处理内存错误"""
        logger.warning("处理内存错误")
        
        # 建议清理内存
        error_context.metadata["cleanup_required"] = True
        error_context.recovery_strategy = RecoveryStrategy.RETRY
        
        # 如果内存错误频繁，建议降级
        if error_context.metadata.get("error_rate", 0) > 2:
            error_context.recovery_strategy = RecoveryStrategy.DEGRADE
    
    def _handle_script_error(self, error_context: ErrorContext):
        """处理脚本错误"""
        logger.warning("处理脚本错误")
        
        # 建议重新生成脚本
        error_context.metadata["regenerate_script"] = True
        
        # 如果脚本错误持续，建议回退
        if error_context.attempt_count >= 2:
            error_context.recovery_strategy = RecoveryStrategy.FALLBACK
    
    def _handle_file_error(self, error_context: ErrorContext):
        """处理文件错误"""
        logger.warning("处理文件错误")
        
        # 检查磁盘空间和权限
        error_context.metadata["check_disk_space"] = True
        error_context.metadata["check_permissions"] = True
    
    def _handle_installation_error(self, error_context: ErrorContext):
        """处理安装错误"""
        logger.warning("处理安装错误")
        
        # 直接回退到默认渲染器
        error_context.recovery_strategy = RecoveryStrategy.FALLBACK
        error_context.severity = ErrorSeverity.HIGH
    
    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """注册恢复策略"""
        self.recovery_strategies[error_type] = strategy
    
    def register_error_callback(self, error_type: str, callback: Callable):
        """注册错误回调"""
        self.error_callbacks[error_type] = callback
    
    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """获取熔断器"""
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker()
        return self.circuit_breakers[service_name]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "total_errors": len(self.error_analyzer.error_history),
            "error_patterns": dict(self.error_analyzer.error_patterns),
            "error_trends": {
                error_type: len(timestamps) 
                for error_type, timestamps in self.error_analyzer.error_trends.items()
            },
            "circuit_breaker_states": {
                name: breaker.state 
                for name, breaker in self.circuit_breakers.items()
            }
        }


# 全局错误处理器实例
global_error_handler = AuditionErrorHandler()
