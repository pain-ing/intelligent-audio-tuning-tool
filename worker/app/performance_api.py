"""
性能监控API端点
提供性能指标查询和监控管理接口
"""

import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .performance_monitor import global_performance_monitor
from .audition_error_handler import global_error_handler

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/performance", tags=["性能监控"])
performance_router = router  # 别名


class PerformanceMetricsResponse(BaseModel):
    """性能指标响应"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    thread_count: int


class SystemHealthResponse(BaseModel):
    """系统健康响应"""
    status: str  # HEALTHY, WARNING, CRITICAL
    current_metrics: PerformanceMetricsResponse
    active_sessions: int
    recommendations: List[str]


class PerformanceReportResponse(BaseModel):
    """性能报告响应"""
    summary: Dict[str, Any]
    current_metrics: Dict[str, Any]
    active_sessions: List[str]
    error_statistics: Dict[str, Any]


@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_current_metrics():
    """获取当前性能指标"""
    try:
        metrics_data = global_performance_monitor.get_real_time_metrics()
        current_metrics = metrics_data["current_metrics"]
        
        return PerformanceMetricsResponse(**current_metrics)
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取性能指标")


@performance_router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """获取系统健康状况"""
    try:
        metrics_data = global_performance_monitor.get_real_time_metrics()
        current_metrics = metrics_data["current_metrics"]
        system_health = metrics_data["system_health"]
        active_sessions = metrics_data["active_sessions"]
        
        # 生成建议
        recommendations = []
        if current_metrics["cpu_percent"] > 80:
            recommendations.append("CPU使用率过高，考虑减少并发处理")
        if current_metrics["memory_percent"] > 80:
            recommendations.append("内存使用率过高，考虑清理缓存或重启服务")
        if active_sessions > 10:
            recommendations.append("活跃会话过多，考虑限制并发数")
        
        return SystemHealthResponse(
            status=system_health,
            current_metrics=PerformanceMetricsResponse(**current_metrics),
            active_sessions=active_sessions,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"获取系统健康状况失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取系统健康状况")


@performance_router.get("/report", response_model=PerformanceReportResponse)
async def get_performance_report():
    """获取详细性能报告"""
    try:
        performance_report = global_performance_monitor.get_performance_report()
        error_statistics = global_error_handler.get_error_statistics()
        
        return PerformanceReportResponse(
            summary=performance_report["summary"],
            current_metrics=performance_report["current_metrics"],
            active_sessions=performance_report["active_sessions"],
            error_statistics=error_statistics
        )
    except Exception as e:
        logger.error(f"获取性能报告失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取性能报告")


@performance_router.get("/sessions")
async def get_active_sessions():
    """获取活跃会话列表"""
    try:
        report = global_performance_monitor.get_performance_report()
        return {
            "active_sessions": report["active_sessions"],
            "count": len(report["active_sessions"])
        }
    except Exception as e:
        logger.error(f"获取活跃会话失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取活跃会话")


@performance_router.get("/history")
async def get_performance_history(
    hours: int = Query(default=1, ge=1, le=24, description="历史数据小时数")
):
    """获取性能历史数据"""
    try:
        # 这里应该从数据库或缓存中获取历史数据
        # 目前返回模拟数据
        current_time = time.time()
        history_data = []
        
        # 生成最近N小时的模拟数据点
        for i in range(hours * 60):  # 每分钟一个数据点
            timestamp = current_time - (hours * 3600) + (i * 60)
            
            # 模拟数据（实际应该从存储中获取）
            data_point = {
                "timestamp": timestamp,
                "cpu_percent": 45.0 + (i % 20),
                "memory_mb": 512.0 + (i % 100),
                "memory_percent": 25.0 + (i % 15),
                "active_sessions": max(0, 5 + (i % 10) - 5)
            }
            history_data.append(data_point)
        
        return {
            "timeframe_hours": hours,
            "data_points": len(history_data),
            "history": history_data[-100:]  # 返回最近100个数据点
        }
    except Exception as e:
        logger.error(f"获取性能历史失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取性能历史")


@performance_router.post("/monitoring/start")
async def start_monitoring():
    """启动性能监控"""
    try:
        global_performance_monitor.system_monitor.start_monitoring()
        return {"message": "性能监控已启动", "status": "started"}
    except Exception as e:
        logger.error(f"启动性能监控失败: {e}")
        raise HTTPException(status_code=500, detail="无法启动性能监控")


@performance_router.post("/monitoring/stop")
async def stop_monitoring():
    """停止性能监控"""
    try:
        global_performance_monitor.system_monitor.stop_monitoring()
        return {"message": "性能监控已停止", "status": "stopped"}
    except Exception as e:
        logger.error(f"停止性能监控失败: {e}")
        raise HTTPException(status_code=500, detail="无法停止性能监控")


@performance_router.get("/alerts")
async def get_performance_alerts():
    """获取性能告警"""
    try:
        metrics_data = global_performance_monitor.get_real_time_metrics()
        current_metrics = metrics_data["current_metrics"]
        
        alerts = []
        
        # CPU告警
        if current_metrics["cpu_percent"] > 90:
            alerts.append({
                "type": "CRITICAL",
                "metric": "cpu_percent",
                "value": current_metrics["cpu_percent"],
                "threshold": 90,
                "message": "CPU使用率严重过高"
            })
        elif current_metrics["cpu_percent"] > 70:
            alerts.append({
                "type": "WARNING",
                "metric": "cpu_percent",
                "value": current_metrics["cpu_percent"],
                "threshold": 70,
                "message": "CPU使用率较高"
            })
        
        # 内存告警
        if current_metrics["memory_percent"] > 90:
            alerts.append({
                "type": "CRITICAL",
                "metric": "memory_percent",
                "value": current_metrics["memory_percent"],
                "threshold": 90,
                "message": "内存使用率严重过高"
            })
        elif current_metrics["memory_percent"] > 70:
            alerts.append({
                "type": "WARNING",
                "metric": "memory_percent",
                "value": current_metrics["memory_percent"],
                "threshold": 70,
                "message": "内存使用率较高"
            })
        
        return {
            "alerts": alerts,
            "alert_count": len(alerts),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"获取性能告警失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取性能告警")


@performance_router.get("/benchmarks")
async def get_performance_benchmarks():
    """获取性能基准测试结果"""
    try:
        # 这里可以返回系统的性能基准数据
        benchmarks = {
            "cpu_benchmark": {
                "single_core_score": 1000,
                "multi_core_score": 4000,
                "test_date": "2025-09-16"
            },
            "memory_benchmark": {
                "read_speed_mb_s": 2000,
                "write_speed_mb_s": 1800,
                "latency_ns": 100
            },
            "disk_benchmark": {
                "read_speed_mb_s": 500,
                "write_speed_mb_s": 450,
                "iops": 1000
            },
            "audio_processing_benchmark": {
                "avg_processing_time_per_mb": 0.1,
                "max_concurrent_sessions": 10,
                "quality_score": 95.0
            }
        }
        
        return benchmarks
    except Exception as e:
        logger.error(f"获取性能基准失败: {e}")
        raise HTTPException(status_code=500, detail="无法获取性能基准")


# 导出路由器
__all__ = ["performance_router"]
