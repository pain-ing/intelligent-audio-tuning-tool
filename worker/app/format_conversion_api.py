"""
音频格式转换API接口
"""

import logging
import os
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from .audio_format_converter import (
    global_format_converter, AudioFormat, AudioQuality, 
    ConversionSettings, AudioMetadata
)
from .batch_processor import global_batch_processor
from .batch_models import BatchTask, AudioProcessingParams

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/format", tags=["音频格式转换"])


# Pydantic模型定义
class ConversionSettingsModel(BaseModel):
    """转换设置模型"""
    target_format: AudioFormat = Field(..., description="目标格式")
    target_sample_rate: Optional[int] = Field(default=None, description="目标采样率")
    target_channels: Optional[int] = Field(default=None, description="目标声道数")
    target_bit_depth: Optional[int] = Field(default=None, description="目标位深度")
    quality: AudioQuality = Field(default=AudioQuality.HIGH, description="音频质量")
    normalize: bool = Field(default=False, description="是否标准化")
    trim_silence: bool = Field(default=False, description="是否修剪静音")
    fade_in: float = Field(default=0.0, description="淡入时间（秒）")
    fade_out: float = Field(default=0.0, description="淡出时间（秒）")
    compression_level: Optional[int] = Field(default=None, description="压缩级别")
    mp3_bitrate: int = Field(default=320, description="MP3比特率")
    aac_bitrate: int = Field(default=256, description="AAC比特率")


class ConversionRequest(BaseModel):
    """转换请求模型"""
    input_path: str = Field(..., description="输入文件路径")
    output_path: str = Field(..., description="输出文件路径")
    settings: ConversionSettingsModel = Field(..., description="转换设置")


class BatchConversionRequest(BaseModel):
    """批量转换请求模型"""
    file_pairs: List[Dict[str, str]] = Field(..., description="文件对列表")
    settings: ConversionSettingsModel = Field(..., description="转换设置")
    use_batch_processor: bool = Field(default=True, description="是否使用批处理器")


class AudioMetadataResponse(BaseModel):
    """音频元数据响应"""
    duration: float
    sample_rate: int
    channels: int
    bit_depth: Optional[int]
    bitrate: Optional[int]
    format: Optional[str]
    file_size: int
    is_stereo: bool
    is_mono: bool


class ConversionEstimateResponse(BaseModel):
    """转换估算响应"""
    input_metadata: AudioMetadataResponse
    estimated_output_size: int
    estimated_processing_time: float
    size_change_percent: float


@router.get("/formats")
async def get_supported_formats():
    """获取支持的音频格式"""
    return {
        "input_formats": list(global_format_converter.supported_input_formats),
        "output_formats": {
            format_enum.value: extensions 
            for format_enum, extensions in global_format_converter.supported_output_formats.items()
        },
        "quality_levels": [quality.value for quality in AudioQuality]
    }


@router.post("/metadata")
async def get_audio_metadata(file_path: str):
    """获取音频文件元数据"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not global_format_converter.is_format_supported(file_path, for_input=True):
            raise HTTPException(status_code=400, detail="不支持的音频格式")
        
        metadata = global_format_converter.get_audio_metadata(file_path)
        
        return AudioMetadataResponse(
            duration=metadata.duration,
            sample_rate=metadata.sample_rate,
            channels=metadata.channels,
            bit_depth=metadata.bit_depth,
            bitrate=metadata.bitrate,
            format=metadata.format,
            file_size=metadata.file_size,
            is_stereo=metadata.is_stereo,
            is_mono=metadata.is_mono
        )
        
    except Exception as e:
        logger.error(f"获取音频元数据失败: {file_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"获取元数据失败: {str(e)}")


@router.post("/estimate")
async def estimate_conversion(request: ConversionRequest):
    """估算转换结果"""
    try:
        if not os.path.exists(request.input_path):
            raise HTTPException(status_code=404, detail="输入文件不存在")
        
        # 转换设置
        settings = ConversionSettings(
            target_format=request.settings.target_format,
            target_sample_rate=request.settings.target_sample_rate,
            target_channels=request.settings.target_channels,
            target_bit_depth=request.settings.target_bit_depth,
            quality=request.settings.quality,
            normalize=request.settings.normalize,
            trim_silence=request.settings.trim_silence,
            fade_in=request.settings.fade_in,
            fade_out=request.settings.fade_out,
            compression_level=request.settings.compression_level,
            mp3_bitrate=request.settings.mp3_bitrate,
            aac_bitrate=request.settings.aac_bitrate
        )
        
        estimate = global_format_converter.get_conversion_estimate(
            request.input_path, settings
        )
        
        return ConversionEstimateResponse(
            input_metadata=AudioMetadataResponse(**estimate["input_metadata"].__dict__),
            estimated_output_size=estimate["estimated_output_size"],
            estimated_processing_time=estimate["estimated_processing_time"],
            size_change_percent=estimate["size_change_percent"]
        )
        
    except Exception as e:
        logger.error(f"转换估算失败: {request.input_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"估算失败: {str(e)}")


@router.post("/convert")
async def convert_audio(request: ConversionRequest):
    """转换音频格式"""
    try:
        if not os.path.exists(request.input_path):
            raise HTTPException(status_code=404, detail="输入文件不存在")
        
        if not global_format_converter.is_format_supported(request.input_path, for_input=True):
            raise HTTPException(status_code=400, detail="不支持的输入格式")
        
        # 转换设置
        settings = ConversionSettings(
            target_format=request.settings.target_format,
            target_sample_rate=request.settings.target_sample_rate,
            target_channels=request.settings.target_channels,
            target_bit_depth=request.settings.target_bit_depth,
            quality=request.settings.quality,
            normalize=request.settings.normalize,
            trim_silence=request.settings.trim_silence,
            fade_in=request.settings.fade_in,
            fade_out=request.settings.fade_out,
            compression_level=request.settings.compression_level,
            mp3_bitrate=request.settings.mp3_bitrate,
            aac_bitrate=request.settings.aac_bitrate
        )
        
        # 执行转换
        result = global_format_converter.convert_audio(
            request.input_path, request.output_path, settings
        )
        
        return {
            "success": result["success"],
            "input_metadata": result["input_metadata"].__dict__,
            "output_metadata": result["output_metadata"].__dict__,
            "size_reduction": result["size_reduction"],
            "output_path": request.output_path
        }
        
    except Exception as e:
        logger.error(f"音频转换失败: {request.input_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.post("/batch-convert")
async def batch_convert_audio(
    request: BatchConversionRequest,
    background_tasks: BackgroundTasks
):
    """批量转换音频格式"""
    try:
        # 验证输入文件
        for file_pair in request.file_pairs:
            input_path = file_pair.get("input_path")
            if not input_path or not os.path.exists(input_path):
                raise HTTPException(
                    status_code=400, 
                    detail=f"输入文件不存在: {input_path}"
                )
            
            if not global_format_converter.is_format_supported(input_path, for_input=True):
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的输入格式: {input_path}"
                )
        
        # 转换设置
        settings = ConversionSettings(
            target_format=request.settings.target_format,
            target_sample_rate=request.settings.target_sample_rate,
            target_channels=request.settings.target_channels,
            target_bit_depth=request.settings.target_bit_depth,
            quality=request.settings.quality,
            normalize=request.settings.normalize,
            trim_silence=request.settings.trim_silence,
            fade_in=request.settings.fade_in,
            fade_out=request.settings.fade_out,
            compression_level=request.settings.compression_level,
            mp3_bitrate=request.settings.mp3_bitrate,
            aac_bitrate=request.settings.aac_bitrate
        )
        
        if request.use_batch_processor:
            # 使用批处理器
            batch_id = await _submit_format_conversion_batch(
                request.file_pairs, settings, background_tasks
            )
            
            return {
                "batch_id": batch_id,
                "message": f"批量转换任务已提交，包含 {len(request.file_pairs)} 个文件",
                "use_batch_processor": True
            }
        else:
            # 直接批量转换
            file_pairs = [
                (pair["input_path"], pair["output_path"]) 
                for pair in request.file_pairs
            ]
            
            results = global_format_converter.batch_convert(file_pairs, settings)
            
            return {
                "results": results,
                "total_files": len(results),
                "successful": sum(1 for r in results if r.get("success", False)),
                "failed": sum(1 for r in results if not r.get("success", False)),
                "use_batch_processor": False
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量转换失败: 错误: {e}")
        raise HTTPException(status_code=500, detail=f"批量转换失败: {str(e)}")


async def _submit_format_conversion_batch(
    file_pairs: List[Dict[str, str]], 
    settings: ConversionSettings,
    background_tasks: BackgroundTasks
) -> str:
    """提交格式转换批处理任务"""
    # 创建批处理任务
    batch_tasks = []
    
    for pair in file_pairs:
        # 创建音频处理参数（包含格式转换设置）
        processing_params = AudioProcessingParams(
            style_params={
                "format_conversion": {
                    "target_format": settings.target_format.value,
                    "target_sample_rate": settings.target_sample_rate,
                    "target_channels": settings.target_channels,
                    "target_bit_depth": settings.target_bit_depth,
                    "quality": settings.quality.value,
                    "normalize": settings.normalize,
                    "trim_silence": settings.trim_silence,
                    "fade_in": settings.fade_in,
                    "fade_out": settings.fade_out,
                    "mp3_bitrate": settings.mp3_bitrate,
                    "aac_bitrate": settings.aac_bitrate
                }
            },
            output_format=settings.target_format.value,
            normalize_audio=settings.normalize
        )
        
        task = BatchTask(
            input_path=pair["input_path"],
            output_path=pair["output_path"],
            processing_params=processing_params
        )
        batch_tasks.append(task)
    
    # 提交批处理
    batch_id = global_batch_processor.submit_batch(batch_tasks)
    
    # 后台启动批处理
    background_tasks.add_task(start_format_conversion_batch, batch_id)
    
    return batch_id


async def start_format_conversion_batch(batch_id: str):
    """启动格式转换批处理"""
    try:
        success = global_batch_processor.start_batch(batch_id)
        if success:
            logger.info(f"格式转换批处理启动成功: {batch_id}")
        else:
            logger.error(f"格式转换批处理启动失败: {batch_id}")
    except Exception as e:
        logger.error(f"格式转换批处理启动异常: {batch_id}, 错误: {e}")


@router.post("/upload-convert")
async def upload_and_convert(
    file: UploadFile = File(...),
    target_format: AudioFormat = Form(...),
    quality: AudioQuality = Form(AudioQuality.HIGH),
    normalize: bool = Form(False)
):
    """上传并转换音频文件"""
    try:
        # 检查文件格式
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in global_format_converter.supported_input_formats:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_ext}")
        
        # 保存上传的文件
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        input_path = os.path.join(upload_dir, file.filename)
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 生成输出文件名
        base_name = os.path.splitext(file.filename)[0]
        output_filename = f"{base_name}_converted.{target_format.value}"
        output_path = os.path.join(upload_dir, output_filename)
        
        # 转换设置
        settings = ConversionSettings(
            target_format=target_format,
            quality=quality,
            normalize=normalize
        )
        
        # 执行转换
        result = global_format_converter.convert_audio(input_path, output_path, settings)
        
        return {
            "success": result["success"],
            "original_filename": file.filename,
            "converted_filename": output_filename,
            "input_metadata": result["input_metadata"].__dict__,
            "output_metadata": result["output_metadata"].__dict__,
            "size_reduction": result["size_reduction"],
            "download_path": f"/api/format/download/{output_filename}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传转换失败: {file.filename}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"上传转换失败: {str(e)}")


@router.get("/download/{filename}")
async def download_converted_file(filename: str):
    """下载转换后的文件"""
    try:
        file_path = os.path.join("uploads", filename)
        
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


@router.delete("/cleanup")
async def cleanup_temp_files(max_age_hours: int = 24):
    """清理临时文件"""
    try:
        import time
        from pathlib import Path
        
        upload_dir = Path("uploads")
        if not upload_dir.exists():
            return {"message": "上传目录不存在"}
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        deleted_count = 0
        for file_path in upload_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
        
        return {"message": f"清理完成，删除了 {deleted_count} 个临时文件"}
        
    except Exception as e:
        logger.error(f"清理临时文件失败: 错误: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")
