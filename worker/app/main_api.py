"""
主API路由器 - 整合所有功能模块
"""

import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 导入所有API模块
from .audition_api import router as audition_router
from .batch_api import router as batch_router
from .format_conversion_api import router as format_router
from .quality_assessment_api import router as quality_router
from .cache_api import router as cache_router
from .performance_api import router as performance_router

logger = logging.getLogger(__name__)

# 创建主路由器
main_router = APIRouter()

# 创建FastAPI应用
app = FastAPI(
    title="Adobe Audition音频处理集成系统",
    description="提供完整的Adobe Audition集成功能，包括音频处理、格式转换、质量评估、批处理和缓存管理",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有API路由
app.include_router(audition_router)
app.include_router(batch_router)
app.include_router(format_router)
app.include_router(quality_router)
app.include_router(cache_router)
app.include_router(performance_router)


@app.get("/")
async def root():
    """根路径 - API概览"""
    return {
        "name": "Adobe Audition音频处理集成系统",
        "version": "1.0.0",
        "description": "提供完整的Adobe Audition集成功能",
        "features": [
            "Adobe Audition集成",
            "音频格式转换",
            "音频质量评估",
            "批量处理",
            "智能缓存",
            "性能监控"
        ],
        "endpoints": {
            "audition": "/api/audition",
            "batch": "/api/batch",
            "format": "/api/format",
            "quality": "/api/quality",
            "cache": "/api/cache",
            "performance": "/api/performance"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/api/system/info")
async def get_system_info():
    """获取系统信息"""
    try:
        from .audition_integration import global_audition_detector
        from .intelligent_cache import global_cache
        from .performance_monitor import global_performance_manager
        
        # 获取各模块状态
        audition_status = global_audition_detector.detect_audition()
        cache_stats = global_cache.get_stats()
        performance_metrics = global_performance_manager.get_current_metrics()
        
        return {
            "system": {
                "name": "Adobe Audition音频处理集成系统",
                "version": "1.0.0",
                "status": "running"
            },
            "modules": {
                "audition_integration": {
                    "status": "available" if audition_status["installed"] else "unavailable",
                    "version": audition_status.get("version"),
                    "path": audition_status.get("path")
                },
                "cache_system": {
                    "status": "active",
                    "entries": cache_stats.total_entries,
                    "size_mb": cache_stats.total_size / 1024 / 1024,
                    "hit_rate": cache_stats.hit_rate
                },
                "performance_monitor": {
                    "status": "active",
                    "cpu_percent": performance_metrics.cpu_percent if performance_metrics else None,
                    "memory_percent": performance_metrics.memory_percent if performance_metrics else None
                },
                "batch_processor": {
                    "status": "active"
                },
                "format_converter": {
                    "status": "active"
                },
                "quality_analyzer": {
                    "status": "active"
                }
            },
            "capabilities": {
                "audio_processing": True,
                "format_conversion": True,
                "quality_assessment": True,
                "batch_processing": True,
                "intelligent_caching": True,
                "performance_monitoring": True,
                "error_handling": True,
                "hot_reload": True
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"获取系统信息失败: {str(e)}"}
        )


@app.get("/api/system/health")
async def get_system_health():
    """获取系统健康状态"""
    try:
        from .audition_integration import global_audition_detector
        from .intelligent_cache import global_cache
        from .performance_monitor import global_performance_manager
        from .audition_error_handler import global_error_handler
        
        # 检查各个组件
        health_checks = {}
        overall_score = 100
        issues = []
        
        # 1. Audition集成检查
        try:
            audition_status = global_audition_detector.detect_audition()
            if audition_status["installed"]:
                health_checks["audition"] = {"status": "healthy", "score": 100}
            else:
                health_checks["audition"] = {"status": "warning", "score": 70}
                overall_score -= 15
                issues.append("Adobe Audition未安装，将使用默认渲染器")
        except Exception as e:
            health_checks["audition"] = {"status": "error", "score": 0, "error": str(e)}
            overall_score -= 30
            issues.append("Audition检测失败")
        
        # 2. 缓存系统检查
        try:
            cache_stats = global_cache.get_stats()
            cache_score = 100
            
            if cache_stats.total_size > 800 * 1024 * 1024:  # 800MB
                cache_score -= 20
                issues.append("缓存大小较大")
            
            if cache_stats.hit_rate < 0.3:
                cache_score -= 15
                issues.append("缓存命中率偏低")
            
            health_checks["cache"] = {"status": "healthy" if cache_score > 80 else "warning", "score": cache_score}
            overall_score -= (100 - cache_score) * 0.2
            
        except Exception as e:
            health_checks["cache"] = {"status": "error", "score": 0, "error": str(e)}
            overall_score -= 20
            issues.append("缓存系统检查失败")
        
        # 3. 性能监控检查
        try:
            performance_metrics = global_performance_manager.get_current_metrics()
            perf_score = 100
            
            if performance_metrics:
                if performance_metrics.cpu_percent > 80:
                    perf_score -= 30
                    issues.append("CPU使用率过高")
                elif performance_metrics.cpu_percent > 60:
                    perf_score -= 15
                    issues.append("CPU使用率较高")
                
                if performance_metrics.memory_percent > 80:
                    perf_score -= 25
                    issues.append("内存使用率过高")
                elif performance_metrics.memory_percent > 60:
                    perf_score -= 10
                    issues.append("内存使用率较高")
            
            health_checks["performance"] = {"status": "healthy" if perf_score > 70 else "warning", "score": perf_score}
            overall_score -= (100 - perf_score) * 0.15
            
        except Exception as e:
            health_checks["performance"] = {"status": "error", "score": 0, "error": str(e)}
            overall_score -= 15
            issues.append("性能监控检查失败")
        
        # 4. 错误处理检查
        try:
            error_stats = global_error_handler.get_error_statistics()
            error_score = 100
            
            if error_stats.get("total_errors", 0) > 100:
                error_score -= 20
                issues.append("错误数量较多")
            
            recent_errors = global_error_handler.get_recent_errors(limit=10)
            if len(recent_errors) > 5:
                error_score -= 15
                issues.append("近期错误频繁")
            
            health_checks["error_handling"] = {"status": "healthy" if error_score > 80 else "warning", "score": error_score}
            overall_score -= (100 - error_score) * 0.1
            
        except Exception as e:
            health_checks["error_handling"] = {"status": "error", "score": 0, "error": str(e)}
            overall_score -= 10
            issues.append("错误处理检查失败")
        
        # 确定整体状态
        if overall_score >= 90:
            overall_status = "healthy"
        elif overall_score >= 70:
            overall_status = "warning"
        else:
            overall_status = "critical"
        
        return {
            "overall_status": overall_status,
            "overall_score": max(0, int(overall_score)),
            "issues": issues,
            "component_health": health_checks,
            "recommendations": _generate_health_recommendations(overall_score, issues),
            "timestamp": performance_metrics.timestamp if performance_metrics else None
        }
        
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "overall_status": "error",
                "overall_score": 0,
                "issues": [f"健康检查失败: {str(e)}"],
                "component_health": {},
                "recommendations": ["检查系统配置和日志"],
                "timestamp": None
            }
        )


def _generate_health_recommendations(score: float, issues: list) -> list:
    """生成健康建议"""
    recommendations = []
    
    if "Adobe Audition未安装" in str(issues):
        recommendations.append("安装Adobe Audition以获得最佳音频处理效果")
    
    if "缓存大小较大" in str(issues):
        recommendations.append("清理缓存或增加缓存大小限制")
    
    if "缓存命中率偏低" in str(issues):
        recommendations.append("检查缓存策略配置")
    
    if "CPU使用率" in str(issues):
        recommendations.append("优化处理参数或增加处理资源")
    
    if "内存使用率" in str(issues):
        recommendations.append("检查内存泄漏或增加系统内存")
    
    if "错误" in str(issues):
        recommendations.append("检查错误日志并修复相关问题")
    
    if score < 70:
        recommendations.append("建议立即检查系统配置和运行状态")
    elif score < 90:
        recommendations.append("建议优化系统配置以提高性能")
    
    if not recommendations:
        recommendations.append("系统运行良好，继续保持")
    
    return recommendations


@app.get("/api/system/stats")
async def get_system_statistics():
    """获取系统统计信息"""
    try:
        from .intelligent_cache import global_cache
        from .performance_monitor import global_performance_manager
        from .audition_error_handler import global_error_handler
        from .batch_processor import global_batch_processor
        
        # 收集各模块统计
        cache_stats = global_cache.get_stats()
        performance_stats = global_performance_manager.get_performance_stats()
        error_stats = global_error_handler.get_error_statistics()
        
        # 批处理统计
        try:
            batch_stats = {
                "total_batches": len(global_batch_processor.batches),
                "active_batches": len([b for b in global_batch_processor.batches.values() 
                                     if b.status.value in ["pending", "running"]]),
                "completed_batches": len([b for b in global_batch_processor.batches.values() 
                                        if b.status.value == "completed"])
            }
        except:
            batch_stats = {"total_batches": 0, "active_batches": 0, "completed_batches": 0}
        
        return {
            "cache": {
                "total_entries": cache_stats.total_entries,
                "total_size_mb": cache_stats.total_size / 1024 / 1024,
                "hit_count": cache_stats.hit_count,
                "miss_count": cache_stats.miss_count,
                "hit_rate": cache_stats.hit_rate,
                "eviction_count": cache_stats.eviction_count
            },
            "performance": performance_stats,
            "errors": error_stats,
            "batch_processing": batch_stats,
            "uptime": performance_stats.get("uptime", 0),
            "requests_processed": cache_stats.hit_count + cache_stats.miss_count
        }
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"获取统计信息失败: {str(e)}"}
        )


# 异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    # 记录到错误处理器
    try:
        from .audition_error_handler import global_error_handler
        global_error_handler.handle_error(exc, {"request_url": str(request.url)})
    except:
        pass
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
