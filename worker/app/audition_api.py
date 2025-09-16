"""
Adobe Audition集成API接口
"""

import logging
import os
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from .audition_integration import global_audition_detector, global_parameter_converter, global_template_manager
from .audition_renderer import create_audition_renderer
from .audition_error_handler import global_error_handler
from .performance_monitor import global_performance_manager
from .config_hot_reload import global_hot_reload_manager
from .intelligent_cache import global_cache_manager, CacheType

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/audition", tags=["Adobe Audition集成"])


# Pydantic模型定义
class AuditionStatusResponse(BaseModel):
    """Audition状态响应"""
    installed: bool = Field(..., description="是否已安装")
    version: Optional[str] = Field(default=None, description="版本信息")
    installation_path: Optional[str] = Field(default=None, description="安装路径")
    supported_features: List[str] = Field(..., description="支持的功能")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class AudioProcessingRequest(BaseModel):
    """音频处理请求"""
    input_path: str = Field(..., description="输入文件路径")
    output_path: str = Field(..., description="输出文件路径")
    style_params: Dict[str, Any] = Field(..., description="风格参数")
    use_cache: bool = Field(default=True, description="是否使用缓存")
    cache_ttl: Optional[float] = Field(default=None, description="缓存生存时间（秒）")


class AudioProcessingResponse(BaseModel):
    """音频处理响应"""
    success: bool = Field(..., description="处理是否成功")
    output_path: str = Field(..., description="输出文件路径")
    processing_time: float = Field(..., description="处理时间（秒）")
    from_cache: bool = Field(..., description="是否来自缓存")
    renderer_used: str = Field(..., description="使用的渲染器")
    performance_metrics: Dict[str, Any] = Field(..., description="性能指标")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class ParameterConversionRequest(BaseModel):
    """参数转换请求"""
    style_params: Dict[str, Any] = Field(..., description="风格参数")
    target_version: Optional[str] = Field(default=None, description="目标Audition版本")


class ParameterConversionResponse(BaseModel):
    """参数转换响应"""
    audition_params: Dict[str, Any] = Field(..., description="Audition参数")
    conversion_notes: List[str] = Field(..., description="转换说明")
    unsupported_params: List[str] = Field(..., description="不支持的参数")


class ScriptGenerationRequest(BaseModel):
    """脚本生成请求"""
    template_name: str = Field(..., description="模板名称")
    parameters: Dict[str, Any] = Field(..., description="参数")
    output_format: str = Field(default="jsx", description="输出格式")


class ScriptGenerationResponse(BaseModel):
    """脚本生成响应"""
    script_content: str = Field(..., description="脚本内容")
    script_path: Optional[str] = Field(default=None, description="脚本文件路径")
    template_used: str = Field(..., description="使用的模板")
    parameters_applied: Dict[str, Any] = Field(..., description="应用的参数")


@router.get("/status", response_model=AuditionStatusResponse)
async def get_audition_status():
    """获取Adobe Audition状态"""
    try:
        # 检测Audition安装
        detection_result = global_audition_detector.detect_audition()
        
        if detection_result["installed"]:
            supported_features = [
                "音频渲染",
                "效果处理",
                "批量处理",
                "脚本自动化",
                "参数转换",
                "模板生成"
            ]
            
            return AuditionStatusResponse(
                installed=True,
                version=detection_result.get("version"),
                installation_path=detection_result.get("path"),
                supported_features=supported_features
            )
        else:
            return AuditionStatusResponse(
                installed=False,
                supported_features=[],
                error_message="Adobe Audition未安装或未找到"
            )
            
    except Exception as e:
        logger.error(f"获取Audition状态失败: {e}")
        return AuditionStatusResponse(
            installed=False,
            supported_features=[],
            error_message=f"状态检查失败: {str(e)}"
        )


@router.post("/process", response_model=AudioProcessingResponse)
async def process_audio(request: AudioProcessingRequest):
    """处理音频文件"""
    try:
        # 验证输入文件
        if not os.path.exists(request.input_path):
            raise HTTPException(status_code=404, detail="输入文件不存在")
        
        # 创建输出目录
        output_dir = os.path.dirname(request.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 开始性能监控
        session_id = global_performance_manager.start_session(
            f"audition_processing_{os.path.basename(request.input_path)}"
        )
        
        try:
            if request.use_cache:
                # 使用缓存管理器处理
                def audition_processor(input_file, output_file, params):
                    renderer = create_audition_renderer()
                    result = renderer.render_audio(input_file, output_file, params)
                    return result.get("success", False)
                
                output_file, from_cache = global_cache_manager.get_or_process_audio(
                    request.input_path,
                    request.style_params,
                    audition_processor,
                    CacheType.AUDITION_RENDERING,
                    output_extension=os.path.splitext(request.output_path)[1],
                    ttl=request.cache_ttl
                )
                
                # 如果输出文件不是请求的路径，复制过去
                if output_file != request.output_path:
                    import shutil
                    shutil.copy2(output_file, request.output_path)
                
                renderer_used = "Audition (缓存)" if from_cache else "Audition"
                
            else:
                # 直接处理，不使用缓存
                renderer = create_audition_renderer()
                result = renderer.render_audio(
                    request.input_path, 
                    request.output_path, 
                    request.style_params
                )
                
                if not result.get("success", False):
                    raise RuntimeError(result.get("error", "音频处理失败"))
                
                from_cache = False
                renderer_used = "Audition"
            
            # 结束性能监控
            session = global_performance_manager.end_session(session_id)
            
            return AudioProcessingResponse(
                success=True,
                output_path=request.output_path,
                processing_time=session.duration if session else 0.0,
                from_cache=from_cache,
                renderer_used=renderer_used,
                performance_metrics=session.__dict__ if session else {}
            )
            
        except Exception as e:
            # 处理失败，记录错误
            global_error_handler.handle_error(e, {"input_path": request.input_path})
            global_performance_manager.end_session(session_id)
            
            raise HTTPException(
                status_code=500, 
                detail=f"音频处理失败: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音频处理请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.post("/convert-parameters", response_model=ParameterConversionResponse)
async def convert_parameters(request: ParameterConversionRequest):
    """转换风格参数为Audition参数"""
    try:
        # 执行参数转换
        conversion_result = global_parameter_converter.convert_parameters(
            request.style_params,
            target_version=request.target_version
        )
        
        return ParameterConversionResponse(
            audition_params=conversion_result["audition_params"],
            conversion_notes=conversion_result.get("notes", []),
            unsupported_params=conversion_result.get("unsupported", [])
        )
        
    except Exception as e:
        logger.error(f"参数转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"参数转换失败: {str(e)}")


@router.post("/generate-script", response_model=ScriptGenerationResponse)
async def generate_script(request: ScriptGenerationRequest):
    """生成Audition脚本"""
    try:
        # 生成脚本
        script_result = global_template_manager.generate_script(
            request.template_name,
            request.parameters,
            output_format=request.output_format
        )
        
        return ScriptGenerationResponse(
            script_content=script_result["content"],
            script_path=script_result.get("file_path"),
            template_used=request.template_name,
            parameters_applied=request.parameters
        )
        
    except Exception as e:
        logger.error(f"脚本生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"脚本生成失败: {str(e)}")


@router.get("/templates")
async def get_available_templates():
    """获取可用的脚本模板"""
    try:
        templates = global_template_manager.get_available_templates()
        
        return {
            "templates": templates,
            "count": len(templates),
            "categories": {
                "effects": [t for t in templates if "effect" in t.lower()],
                "processing": [t for t in templates if "process" in t.lower()],
                "utility": [t for t in templates if t not in 
                          [t2 for t2 in templates if "effect" in t2.lower() or "process" in t2.lower()]]
            }
        }
        
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")


@router.get("/performance")
async def get_performance_metrics():
    """获取性能指标"""
    try:
        # 获取当前性能状态
        current_metrics = global_performance_manager.get_current_metrics()
        
        # 获取历史统计
        stats = global_performance_manager.get_performance_stats()
        
        return {
            "current_metrics": current_metrics.__dict__ if current_metrics else {},
            "statistics": stats,
            "active_sessions": len(global_performance_manager.active_sessions),
            "system_health": "healthy" if current_metrics and current_metrics.cpu_percent < 80 else "warning"
        }
        
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")


@router.get("/errors")
async def get_error_statistics():
    """获取错误统计"""
    try:
        error_stats = global_error_handler.get_error_statistics()
        recent_errors = global_error_handler.get_recent_errors(limit=10)
        
        return {
            "statistics": error_stats,
            "recent_errors": recent_errors,
            "error_trends": global_error_handler.analyze_error_trends()
        }
        
    except Exception as e:
        logger.error(f"获取错误统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取错误统计失败: {str(e)}")


@router.post("/reload-config")
async def reload_configuration():
    """重新加载配置"""
    try:
        # 触发配置重载
        success = global_hot_reload_manager.reload_all_configs()
        
        if success:
            return {
                "success": True,
                "message": "配置重载成功",
                "timestamp": global_hot_reload_manager.get_status()["last_reload"]
            }
        else:
            raise HTTPException(status_code=500, detail="配置重载失败")
            
    except Exception as e:
        logger.error(f"配置重载失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置重载失败: {str(e)}")


@router.get("/config-status")
async def get_config_status():
    """获取配置状态"""
    try:
        status = global_hot_reload_manager.get_status()
        
        return {
            "hot_reload_enabled": status["enabled"],
            "last_reload": status["last_reload"],
            "watched_files": status["watched_files"],
            "reload_count": status["reload_count"],
            "config_health": "healthy" if status["enabled"] else "disabled"
        }
        
    except Exception as e:
        logger.error(f"获取配置状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置状态失败: {str(e)}")


@router.post("/upload-process")
async def upload_and_process(
    file: UploadFile = File(...),
    style_params: str = Form(...),
    use_cache: bool = Form(True)
):
    """上传并处理音频文件"""
    try:
        import json
        import tempfile
        
        # 解析风格参数
        try:
            style_params_dict = json.loads(style_params)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="风格参数格式错误")
        
        # 检查文件格式
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        supported_formats = {".wav", ".mp3", ".flac", ".aac", ".ogg", ".m4a"}
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件格式: {file_ext}"
            )
        
        # 保存上传的文件
        upload_dir = "uploads/audition"
        os.makedirs(upload_dir, exist_ok=True)
        
        input_path = os.path.join(upload_dir, file.filename)
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # 生成输出文件名
            base_name = os.path.splitext(file.filename)[0]
            output_filename = f"{base_name}_processed{file_ext}"
            output_path = os.path.join(upload_dir, output_filename)
            
            # 处理音频
            request = AudioProcessingRequest(
                input_path=input_path,
                output_path=output_path,
                style_params=style_params_dict,
                use_cache=use_cache
            )
            
            result = await process_audio(request)
            
            # 添加下载信息
            result_dict = result.dict()
            result_dict["download_url"] = f"/api/audition/download/{output_filename}"
            result_dict["original_filename"] = file.filename
            result_dict["processed_filename"] = output_filename
            
            return result_dict
            
        finally:
            # 清理输入文件
            if os.path.exists(input_path):
                os.remove(input_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传处理失败: {file.filename}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"上传处理失败: {str(e)}")


@router.get("/download/{filename}")
async def download_processed_file(filename: str):
    """下载处理后的文件"""
    try:
        file_path = os.path.join("uploads/audition", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {filename}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查各个组件状态
        audition_status = global_audition_detector.detect_audition()
        performance_metrics = global_performance_manager.get_current_metrics()
        config_status = global_hot_reload_manager.get_status()
        
        # 计算健康分数
        health_score = 100
        issues = []
        
        # 检查Audition状态
        if not audition_status["installed"]:
            health_score -= 30
            issues.append("Adobe Audition未安装")
        
        # 检查性能
        if performance_metrics and performance_metrics.cpu_percent > 80:
            health_score -= 20
            issues.append("CPU使用率过高")
        
        if performance_metrics and performance_metrics.memory_percent > 80:
            health_score -= 15
            issues.append("内存使用率过高")
        
        # 检查配置
        if not config_status["enabled"]:
            health_score -= 10
            issues.append("配置热重载未启用")
        
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
            "components": {
                "audition": "available" if audition_status["installed"] else "unavailable",
                "performance_monitor": "active",
                "config_manager": "active" if config_status["enabled"] else "inactive",
                "error_handler": "active",
                "cache_system": "active"
            },
            "timestamp": global_performance_manager.get_current_metrics().timestamp if performance_metrics else None
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "health_score": 0,
            "issues": [f"健康检查失败: {str(e)}"],
            "components": {},
            "timestamp": None
        }
