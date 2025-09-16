"""
性能监控模块
提供实时性能监控、指标收集和性能分析功能
"""

import time
import threading
import queue
import psutil
import logging
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    process_count: int = 0
    thread_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "memory_percent": self.memory_percent,
            "disk_io_read_mb": self.disk_io_read_mb,
            "disk_io_write_mb": self.disk_io_write_mb,
            "network_sent_mb": self.network_sent_mb,
            "network_recv_mb": self.network_recv_mb,
            "process_count": self.process_count,
            "thread_count": self.thread_count
        }


@dataclass
class ProcessingSession:
    """处理会话"""
    session_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    operation_type: str = "unknown"
    input_size: int = 0
    output_size: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    metrics_history: List[PerformanceMetrics] = field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """获取持续时间"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def finalize(self, success: bool = True, error_message: Optional[str] = None):
        """完成会话"""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, sampling_interval: float = 1.0):
        self.sampling_interval = sampling_interval
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics_queue = queue.Queue()
        self.monitor_thread = None
        
        # 初始化基线指标
        self._baseline_disk_io = psutil.disk_io_counters()
        self._baseline_network = psutil.net_io_counters()
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("系统监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("系统监控已停止")
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前指标"""
        try:
            # CPU和内存
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # 磁盘IO
            disk_io = psutil.disk_io_counters()
            disk_read_mb = (disk_io.read_bytes - self._baseline_disk_io.read_bytes) / 1024 / 1024
            disk_write_mb = (disk_io.write_bytes - self._baseline_disk_io.write_bytes) / 1024 / 1024
            
            # 网络IO
            network_io = psutil.net_io_counters()
            network_sent_mb = (network_io.bytes_sent - self._baseline_network.bytes_sent) / 1024 / 1024
            network_recv_mb = (network_io.bytes_recv - self._baseline_network.bytes_recv) / 1024 / 1024
            
            # 进程和线程
            process_count = len(psutil.pids())
            thread_count = self.process.num_threads()
            
            return PerformanceMetrics(
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_sent_mb=network_sent_mb,
                network_recv_mb=network_recv_mb,
                process_count=process_count,
                thread_count=thread_count
            )
        except Exception as e:
            logger.warning(f"获取性能指标失败: {e}")
            return PerformanceMetrics()
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                metrics = self.get_current_metrics()
                self.metrics_queue.put(metrics)
                time.sleep(self.sampling_interval)
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                break
    
    def get_metrics_history(self) -> List[PerformanceMetrics]:
        """获取指标历史"""
        history = []
        while not self.metrics_queue.empty():
            try:
                metrics = self.metrics_queue.get_nowait()
                history.append(metrics)
            except queue.Empty:
                break
        return history


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.sessions_history = deque(maxlen=history_size)
        self.metrics_aggregator = defaultdict(list)
    
    def analyze_session(self, session: ProcessingSession) -> Dict[str, Any]:
        """分析处理会话"""
        self.sessions_history.append(session)
        
        analysis = {
            "session_id": session.session_id,
            "duration": session.duration,
            "success": session.success,
            "throughput_mb_per_sec": 0.0,
            "avg_cpu_percent": 0.0,
            "max_memory_mb": 0.0,
            "avg_memory_mb": 0.0,
            "performance_score": 0.0,
            "bottlenecks": []
        }
        
        if session.metrics_history:
            # 计算平均CPU使用率
            cpu_values = [m.cpu_percent for m in session.metrics_history]
            analysis["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
            
            # 计算内存使用情况
            memory_values = [m.memory_mb for m in session.metrics_history]
            analysis["max_memory_mb"] = max(memory_values)
            analysis["avg_memory_mb"] = sum(memory_values) / len(memory_values)
            
            # 计算吞吐量
            if session.duration > 0 and session.input_size > 0:
                throughput = (session.input_size / 1024 / 1024) / session.duration
                analysis["throughput_mb_per_sec"] = throughput
            
            # 性能评分（0-100）
            analysis["performance_score"] = self._calculate_performance_score(session)
            
            # 识别瓶颈
            analysis["bottlenecks"] = self._identify_bottlenecks(session)
        
        return analysis
    
    def _calculate_performance_score(self, session: ProcessingSession) -> float:
        """计算性能评分"""
        if not session.metrics_history:
            return 0.0
        
        score = 100.0
        
        # CPU使用率评分（理想范围：30-70%）
        avg_cpu = sum(m.cpu_percent for m in session.metrics_history) / len(session.metrics_history)
        if avg_cpu < 30:
            score -= (30 - avg_cpu) * 0.5  # CPU利用率不足
        elif avg_cpu > 70:
            score -= (avg_cpu - 70) * 1.0  # CPU过载
        
        # 内存使用评分（避免超过80%）
        max_memory_percent = max(m.memory_percent for m in session.metrics_history)
        if max_memory_percent > 80:
            score -= (max_memory_percent - 80) * 2.0
        
        # 处理时间评分（基于文件大小）
        if session.input_size > 0 and session.duration > 0:
            expected_time = (session.input_size / 1024 / 1024) * 0.1  # 假设每MB需要0.1秒
            if session.duration > expected_time * 2:
                score -= 20  # 处理时间过长
        
        return max(0.0, min(100.0, score))
    
    def _identify_bottlenecks(self, session: ProcessingSession) -> List[str]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        if not session.metrics_history:
            return bottlenecks
        
        # CPU瓶颈
        avg_cpu = sum(m.cpu_percent for m in session.metrics_history) / len(session.metrics_history)
        if avg_cpu > 80:
            bottlenecks.append("CPU_OVERLOAD")
        elif avg_cpu < 20:
            bottlenecks.append("CPU_UNDERUTILIZED")
        
        # 内存瓶颈
        max_memory_percent = max(m.memory_percent for m in session.metrics_history)
        if max_memory_percent > 85:
            bottlenecks.append("MEMORY_PRESSURE")
        
        # IO瓶颈
        total_disk_io = sum(m.disk_io_read_mb + m.disk_io_write_mb for m in session.metrics_history)
        if total_disk_io > 100:  # 超过100MB的IO
            bottlenecks.append("DISK_IO_INTENSIVE")
        
        return bottlenecks
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.sessions_history:
            return {"message": "暂无性能数据"}
        
        successful_sessions = [s for s in self.sessions_history if s.success]
        failed_sessions = [s for s in self.sessions_history if not s.success]
        
        summary = {
            "total_sessions": len(self.sessions_history),
            "successful_sessions": len(successful_sessions),
            "failed_sessions": len(failed_sessions),
            "success_rate": len(successful_sessions) / len(self.sessions_history) * 100,
            "avg_duration": 0.0,
            "avg_throughput": 0.0,
            "avg_performance_score": 0.0
        }
        
        if successful_sessions:
            durations = [s.duration for s in successful_sessions]
            summary["avg_duration"] = sum(durations) / len(durations)
            
            # 计算平均吞吐量
            throughputs = []
            for s in successful_sessions:
                if s.duration > 0 and s.input_size > 0:
                    throughput = (s.input_size / 1024 / 1024) / s.duration
                    throughputs.append(throughput)
            
            if throughputs:
                summary["avg_throughput"] = sum(throughputs) / len(throughputs)
            
            # 计算平均性能评分
            scores = [self._calculate_performance_score(s) for s in successful_sessions]
            summary["avg_performance_score"] = sum(scores) / len(scores)
        
        return summary


class PerformanceMonitorManager:
    """性能监控管理器"""
    
    def __init__(self):
        self.system_monitor = SystemMonitor()
        self.analyzer = PerformanceAnalyzer()
        self.active_sessions = {}
        self._lock = threading.Lock()
    
    @contextmanager
    def monitor_session(self, session_id: str, operation_type: str = "unknown", **kwargs):
        """监控会话上下文管理器"""
        session = ProcessingSession(
            session_id=session_id,
            operation_type=operation_type,
            parameters=kwargs
        )
        
        with self._lock:
            self.active_sessions[session_id] = session
        
        # 开始监控
        self.system_monitor.start_monitoring()
        
        try:
            yield session
            session.finalize(success=True)
        except Exception as e:
            session.finalize(success=False, error_message=str(e))
            raise
        finally:
            # 收集监控数据
            session.metrics_history = self.system_monitor.get_metrics_history()
            
            # 分析会话
            analysis = self.analyzer.analyze_session(session)
            logger.info(f"会话 {session_id} 完成，性能评分: {analysis['performance_score']:.1f}")
            
            with self._lock:
                self.active_sessions.pop(session_id, None)
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """获取实时指标"""
        current_metrics = self.system_monitor.get_current_metrics()
        
        return {
            "current_metrics": current_metrics.to_dict(),
            "active_sessions": len(self.active_sessions),
            "system_health": self._assess_system_health(current_metrics)
        }
    
    def _assess_system_health(self, metrics: PerformanceMetrics) -> str:
        """评估系统健康状况"""
        if metrics.cpu_percent > 90 or metrics.memory_percent > 90:
            return "CRITICAL"
        elif metrics.cpu_percent > 70 or metrics.memory_percent > 70:
            return "WARNING"
        else:
            return "HEALTHY"
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            "summary": self.analyzer.get_performance_summary(),
            "current_metrics": self.get_real_time_metrics(),
            "active_sessions": list(self.active_sessions.keys())
        }


# 全局性能监控管理器
global_performance_monitor = PerformanceMonitorManager()
global_performance_manager = global_performance_monitor  # 别名
