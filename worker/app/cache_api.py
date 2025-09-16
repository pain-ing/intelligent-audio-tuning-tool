"""
缓存管理API接口
"""

import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .intelligent_cache import (
    global_cache, global_cache_manager, CacheType, CacheStats
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/cache", tags=["缓存管理"])


# Pydantic模型定义
class CacheStatsResponse(BaseModel):
    """缓存统计响应模型"""
    total_entries: int = Field(..., description="总条目数")
    total_size: int = Field(..., description="总大小（字节）")
    total_size_mb: float = Field(..., description="总大小（MB）")
    hit_count: int = Field(..., description="命中次数")
    miss_count: int = Field(..., description="未命中次数")
    eviction_count: int = Field(..., description="驱逐次数")
    hit_rate: float = Field(..., description="命中率")
    average_size: float = Field(..., description="平均文件大小（字节）")


class CacheEntryInfo(BaseModel):
    """缓存条目信息"""
    cache_key: str = Field(..., description="缓存键")
    cache_type: str = Field(..., description="缓存类型")
    created_at: float = Field(..., description="创建时间")
    last_accessed: float = Field(..., description="最后访问时间")
    access_count: int = Field(..., description="访问次数")
    file_size: int = Field(..., description="文件大小（字节）")
    ttl: Optional[float] = Field(default=None, description="生存时间（秒）")
    age: float = Field(..., description="缓存年龄（秒）")
    last_access_age: float = Field(..., description="最后访问年龄（秒）")


class ClearCacheRequest(BaseModel):
    """清理缓存请求"""
    cache_type: Optional[str] = Field(default=None, description="缓存类型（可选）")


class WarmCacheRequest(BaseModel):
    """预热缓存请求"""
    input_files: List[str] = Field(..., description="输入文件列表")
    params_list: List[Dict[str, Any]] = Field(..., description="参数列表")
    cache_type: str = Field(..., description="缓存类型")
    processor_type: str = Field(..., description="处理器类型")


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        stats = global_cache.get_stats()
        
        return CacheStatsResponse(
            total_entries=stats.total_entries,
            total_size=stats.total_size,
            total_size_mb=stats.total_size / 1024 / 1024,
            hit_count=stats.hit_count,
            miss_count=stats.miss_count,
            eviction_count=stats.eviction_count,
            hit_rate=stats.hit_rate,
            average_size=stats.average_size
        )
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.get("/entries", response_model=List[CacheEntryInfo])
async def get_cache_entries(cache_type: Optional[str] = None, limit: int = 100):
    """获取缓存条目信息"""
    try:
        # 转换缓存类型
        cache_type_enum = None
        if cache_type:
            try:
                cache_type_enum = CacheType(cache_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的缓存类型: {cache_type}")
        
        # 获取缓存信息
        entries = global_cache.get_cache_info(cache_type_enum)
        
        # 限制返回数量
        entries = entries[:limit]
        
        # 转换为响应模型
        result = []
        for entry in entries:
            result.append(CacheEntryInfo(
                cache_key=entry["cache_key"],
                cache_type=entry["cache_type"],
                created_at=entry["created_at"],
                last_accessed=entry["last_accessed"],
                access_count=entry["access_count"],
                file_size=entry["file_size"],
                ttl=entry["ttl"],
                age=entry["age"],
                last_access_age=entry["last_access_age"]
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存条目失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取条目失败: {str(e)}")


@router.post("/clear")
async def clear_cache(request: ClearCacheRequest):
    """清理缓存"""
    try:
        # 转换缓存类型
        cache_type_enum = None
        if request.cache_type:
            try:
                cache_type_enum = CacheType(request.cache_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的缓存类型: {request.cache_type}")
        
        # 清理缓存
        deleted_count = global_cache.clear_cache(cache_type_enum)
        
        return {
            "message": f"缓存清理完成",
            "deleted_count": deleted_count,
            "cache_type": request.cache_type or "all"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/types")
async def get_cache_types():
    """获取支持的缓存类型"""
    return {
        "cache_types": [cache_type.value for cache_type in CacheType],
        "descriptions": {
            CacheType.AUDIO_PROCESSING.value: "音频处理缓存",
            CacheType.FORMAT_CONVERSION.value: "格式转换缓存",
            CacheType.QUALITY_ANALYSIS.value: "质量分析缓存",
            CacheType.BATCH_PROCESSING.value: "批处理缓存",
            CacheType.AUDITION_RENDERING.value: "Audition渲染缓存"
        }
    }


@router.post("/warm")
async def warm_cache(
    request: WarmCacheRequest,
    background_tasks: BackgroundTasks
):
    """预热缓存"""
    try:
        # 验证缓存类型
        try:
            cache_type_enum = CacheType(request.cache_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的缓存类型: {request.cache_type}")
        
        # 验证文件数量和参数数量匹配
        if len(request.input_files) != len(request.params_list):
            raise HTTPException(
                status_code=400, 
                detail="输入文件数量与参数数量不匹配"
            )
        
        # 验证文件存在
        missing_files = []
        for file_path in request.input_files:
            import os
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            raise HTTPException(
                status_code=400,
                detail=f"以下文件不存在: {missing_files[:5]}"  # 只显示前5个
            )
        
        # 启动后台预热任务
        background_tasks.add_task(
            _perform_cache_warming,
            request.input_files,
            request.params_list,
            cache_type_enum,
            request.processor_type
        )
        
        return {
            "message": "缓存预热任务已启动",
            "file_count": len(request.input_files),
            "cache_type": request.cache_type,
            "processor_type": request.processor_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动缓存预热失败: {e}")
        raise HTTPException(status_code=500, detail=f"预热启动失败: {str(e)}")


async def _perform_cache_warming(
    input_files: List[str],
    params_list: List[Dict[str, Any]],
    cache_type: CacheType,
    processor_type: str
):
    """执行缓存预热"""
    try:
        # 根据处理器类型选择处理函数
        processor_func = _get_processor_function(processor_type)
        
        if processor_func:
            global_cache_manager.warm_cache(
                input_files, params_list, processor_func, cache_type
            )
        else:
            logger.error(f"未知的处理器类型: {processor_type}")
        
    except Exception as e:
        logger.error(f"缓存预热异常: {e}")


def _get_processor_function(processor_type: str):
    """获取处理器函数"""
    # 这里可以根据处理器类型返回相应的处理函数
    # 为了演示，返回一个简单的处理函数
    
    if processor_type == "audio_processing":
        from .audio_rendering import create_audio_renderer
        
        def audio_processor(input_file, output_file, params):
            try:
                renderer = create_audio_renderer()
                result = renderer.render_audio(input_file, output_file, params.get("style_params", {}))
                return result.get("success", False)
            except:
                return False
        
        return audio_processor
    
    elif processor_type == "format_conversion":
        from .audio_format_converter import global_format_converter, ConversionSettings, AudioFormat
        
        def format_processor(input_file, output_file, params):
            try:
                settings = ConversionSettings(
                    target_format=AudioFormat(params.get("target_format", "wav")),
                    quality=params.get("quality", "high")
                )
                result = global_format_converter.convert_audio(input_file, output_file, settings)
                return result.get("success", False)
            except:
                return False
        
        return format_processor
    
    elif processor_type == "quality_analysis":
        from .audio_quality_analyzer import global_quality_analyzer
        
        def quality_processor(input_file, output_file, params):
            try:
                # 质量分析不产生输出文件，这里创建一个JSON结果文件
                import json
                metrics = global_quality_analyzer.analyze_audio_quality(input_file)
                
                with open(output_file, 'w') as f:
                    json.dump(metrics.__dict__, f, indent=2)
                
                return True
            except:
                return False
        
        return quality_processor
    
    return None


@router.get("/health")
async def cache_health_check():
    """缓存系统健康检查"""
    try:
        stats = global_cache.get_stats()
        
        # 计算健康指标
        health_score = 100
        issues = []
        
        # 检查命中率
        if stats.hit_rate < 0.5:
            health_score -= 20
            issues.append("缓存命中率偏低")
        
        # 检查缓存大小
        cache_size_mb = stats.total_size / 1024 / 1024
        if cache_size_mb > 800:  # 假设最大1GB，80%为警告线
            health_score -= 15
            issues.append("缓存大小接近限制")
        
        # 检查条目数
        if stats.total_entries > 8000:  # 假设最大10000，80%为警告线
            health_score -= 10
            issues.append("缓存条目数较多")
        
        # 确定健康状态
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "status": status,
            "health_score": health_score,
            "issues": issues,
            "stats": {
                "total_entries": stats.total_entries,
                "total_size_mb": cache_size_mb,
                "hit_rate": stats.hit_rate,
                "hit_count": stats.hit_count,
                "miss_count": stats.miss_count
            },
            "recommendations": _get_health_recommendations(health_score, issues)
        }
        
    except Exception as e:
        logger.error(f"缓存健康检查失败: {e}")
        return {
            "status": "error",
            "health_score": 0,
            "issues": [f"健康检查失败: {str(e)}"],
            "stats": {},
            "recommendations": ["检查缓存系统配置"]
        }


def _get_health_recommendations(health_score: int, issues: List[str]) -> List[str]:
    """获取健康建议"""
    recommendations = []
    
    if "缓存命中率偏低" in issues:
        recommendations.append("考虑调整缓存策略或增加缓存大小")
    
    if "缓存大小接近限制" in issues:
        recommendations.append("清理旧缓存或增加缓存大小限制")
    
    if "缓存条目数较多" in issues:
        recommendations.append("清理不常用的缓存条目")
    
    if health_score < 70:
        recommendations.append("建议立即检查缓存系统配置")
    
    if not recommendations:
        recommendations.append("缓存系统运行良好")
    
    return recommendations
