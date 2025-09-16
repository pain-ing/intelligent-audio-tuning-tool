"""
音频质量评估API接口
"""

import logging
import os
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from .audio_quality_analyzer import (
    global_quality_analyzer, QualityMetrics, QualityComparison, QualityMetric
)

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/quality", tags=["音频质量评估"])


# Pydantic模型定义
class QualityMetricsResponse(BaseModel):
    """质量指标响应模型"""
    # 基础指标
    snr: float = Field(..., description="信噪比 (dB)")
    thd: float = Field(..., description="总谐波失真 (%)")
    dynamic_range: float = Field(..., description="动态范围 (dB)")
    peak_level: float = Field(..., description="峰值电平 (dB)")
    rms_level: float = Field(..., description="RMS电平 (dB)")
    
    # 频域指标
    frequency_response_flatness: float = Field(..., description="频率响应平坦度")
    spectral_centroid: float = Field(..., description="频谱质心 (Hz)")
    spectral_rolloff: float = Field(..., description="频谱滚降 (Hz)")
    spectral_bandwidth: float = Field(..., description="频谱带宽 (Hz)")
    
    # 时域指标
    zero_crossing_rate: float = Field(..., description="过零率")
    tempo: Optional[float] = Field(default=None, description="节拍 (BPM)")
    
    # 立体声指标
    stereo_width: float = Field(..., description="立体声宽度")
    phase_correlation: float = Field(..., description="相位相关性")
    
    # 感知指标
    loudness_lufs: float = Field(..., description="响度 (LUFS)")
    perceived_quality_score: float = Field(..., description="感知质量评分 (0-100)")
    
    # MFCC特征
    mfcc_features: List[float] = Field(..., description="MFCC特征")
    
    # 元数据
    duration: float = Field(..., description="时长 (秒)")
    sample_rate: int = Field(..., description="采样率 (Hz)")
    channels: int = Field(..., description="声道数")
    bit_depth: Optional[int] = Field(default=None, description="位深度")


class QualityComparisonResponse(BaseModel):
    """质量对比响应模型"""
    original_metrics: QualityMetricsResponse
    processed_metrics: QualityMetricsResponse
    
    # 对比指标
    snr_change: float = Field(..., description="信噪比变化 (dB)")
    thd_change: float = Field(..., description="总谐波失真变化 (%)")
    dynamic_range_change: float = Field(..., description="动态范围变化 (dB)")
    loudness_change: float = Field(..., description="响度变化 (LUFS)")
    
    # 整体评估
    overall_quality_change: float = Field(..., description="整体质量变化 (-100 到 100)")
    quality_grade: str = Field(..., description="质量等级")
    
    # 详细分析
    improvements: List[str] = Field(..., description="改进项目")
    degradations: List[str] = Field(..., description="退化项目")
    recommendations: List[str] = Field(..., description="优化建议")


class QualityAnalysisRequest(BaseModel):
    """质量分析请求模型"""
    file_path: str = Field(..., description="音频文件路径")
    metrics: Optional[List[QualityMetric]] = Field(default=None, description="指定分析的指标")


class QualityComparisonRequest(BaseModel):
    """质量对比请求模型"""
    original_path: str = Field(..., description="原始文件路径")
    processed_path: str = Field(..., description="处理后文件路径")


def _convert_metrics_to_response(metrics: QualityMetrics) -> QualityMetricsResponse:
    """转换质量指标为响应模型"""
    return QualityMetricsResponse(
        snr=metrics.snr,
        thd=metrics.thd,
        dynamic_range=metrics.dynamic_range,
        peak_level=metrics.peak_level,
        rms_level=metrics.rms_level,
        frequency_response_flatness=metrics.frequency_response_flatness,
        spectral_centroid=metrics.spectral_centroid,
        spectral_rolloff=metrics.spectral_rolloff,
        spectral_bandwidth=metrics.spectral_bandwidth,
        zero_crossing_rate=metrics.zero_crossing_rate,
        tempo=metrics.tempo,
        stereo_width=metrics.stereo_width,
        phase_correlation=metrics.phase_correlation,
        loudness_lufs=metrics.loudness_lufs,
        perceived_quality_score=metrics.perceived_quality_score,
        mfcc_features=metrics.mfcc_features,
        duration=metrics.duration,
        sample_rate=metrics.sample_rate,
        channels=metrics.channels,
        bit_depth=metrics.bit_depth
    )


@router.get("/metrics")
async def get_supported_metrics():
    """获取支持的质量评估指标"""
    return {
        "metrics": [metric.value for metric in QualityMetric],
        "descriptions": {
            QualityMetric.SNR.value: "信噪比 - 信号与噪声的比值",
            QualityMetric.THD.value: "总谐波失真 - 音频失真程度",
            QualityMetric.DYNAMIC_RANGE.value: "动态范围 - 最大与最小信号的比值",
            QualityMetric.FREQUENCY_RESPONSE.value: "频率响应 - 频率特性分析",
            QualityMetric.STEREO_IMAGING.value: "立体声成像 - 空间定位效果",
            QualityMetric.LOUDNESS.value: "响度 - 感知音量大小",
            QualityMetric.SPECTRAL_CENTROID.value: "频谱质心 - 频谱重心位置",
            QualityMetric.SPECTRAL_ROLLOFF.value: "频谱滚降 - 高频衰减特性",
            QualityMetric.ZERO_CROSSING_RATE.value: "过零率 - 信号过零频率",
            QualityMetric.MFCC.value: "MFCC - 梅尔频率倒谱系数"
        }
    }


@router.post("/analyze", response_model=QualityMetricsResponse)
async def analyze_audio_quality(request: QualityAnalysisRequest):
    """分析音频质量"""
    try:
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="音频文件不存在")
        
        # 执行质量分析
        metrics = global_quality_analyzer.analyze_audio_quality(request.file_path)
        
        return _convert_metrics_to_response(metrics)
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="音频文件不存在")
    except Exception as e:
        logger.error(f"音频质量分析失败: {request.file_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"质量分析失败: {str(e)}")


@router.post("/compare", response_model=QualityComparisonResponse)
async def compare_audio_quality(request: QualityComparisonRequest):
    """对比音频质量"""
    try:
        if not os.path.exists(request.original_path):
            raise HTTPException(status_code=404, detail="原始音频文件不存在")
        
        if not os.path.exists(request.processed_path):
            raise HTTPException(status_code=404, detail="处理后音频文件不存在")
        
        # 执行质量对比
        comparison = global_quality_analyzer.compare_audio_quality(
            request.original_path, request.processed_path
        )
        
        return QualityComparisonResponse(
            original_metrics=_convert_metrics_to_response(comparison.original_metrics),
            processed_metrics=_convert_metrics_to_response(comparison.processed_metrics),
            snr_change=comparison.snr_change,
            thd_change=comparison.thd_change,
            dynamic_range_change=comparison.dynamic_range_change,
            loudness_change=comparison.loudness_change,
            overall_quality_change=comparison.overall_quality_change,
            quality_grade=comparison.quality_grade,
            improvements=comparison.improvements,
            degradations=comparison.degradations,
            recommendations=comparison.recommendations
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"音频质量对比失败: {request.original_path} vs {request.processed_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"质量对比失败: {str(e)}")


@router.post("/batch-analyze")
async def batch_analyze_quality(
    file_paths: List[str],
    background_tasks: BackgroundTasks
):
    """批量分析音频质量"""
    try:
        # 验证文件存在
        missing_files = [path for path in file_paths if not os.path.exists(path)]
        if missing_files:
            raise HTTPException(
                status_code=400, 
                detail=f"以下文件不存在: {missing_files}"
            )
        
        # 启动后台批量分析
        task_id = f"quality_batch_{len(file_paths)}_{hash(tuple(file_paths))}"
        background_tasks.add_task(
            _perform_batch_quality_analysis, 
            task_id, 
            file_paths
        )
        
        return {
            "task_id": task_id,
            "message": f"批量质量分析任务已启动，包含 {len(file_paths)} 个文件",
            "file_count": len(file_paths)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量质量分析启动失败: 错误: {e}")
        raise HTTPException(status_code=500, detail=f"批量分析启动失败: {str(e)}")


async def _perform_batch_quality_analysis(task_id: str, file_paths: List[str]):
    """执行批量质量分析"""
    try:
        results = {}
        
        for i, file_path in enumerate(file_paths):
            try:
                logger.info(f"批量质量分析进度: {i+1}/{len(file_paths)} - {file_path}")
                metrics = global_quality_analyzer.analyze_audio_quality(file_path)
                results[file_path] = {
                    "success": True,
                    "metrics": metrics.__dict__
                }
            except Exception as e:
                logger.error(f"文件质量分析失败: {file_path}, 错误: {e}")
                results[file_path] = {
                    "success": False,
                    "error": str(e)
                }
        
        # 保存结果（这里可以保存到数据库或缓存）
        logger.info(f"批量质量分析完成: {task_id}, 成功: {sum(1 for r in results.values() if r['success'])}/{len(results)}")
        
    except Exception as e:
        logger.error(f"批量质量分析异常: {task_id}, 错误: {e}")


@router.post("/upload-analyze")
async def upload_and_analyze(
    file: UploadFile = File(...),
    detailed_analysis: bool = Form(True)
):
    """上传并分析音频质量"""
    try:
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
        upload_dir = "uploads/quality"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # 执行质量分析
            metrics = global_quality_analyzer.analyze_audio_quality(file_path)
            
            response = _convert_metrics_to_response(metrics)
            
            # 添加额外信息
            result = {
                "filename": file.filename,
                "file_size": len(content),
                "analysis_results": response.dict(),
                "quality_summary": {
                    "grade": global_quality_analyzer._determine_quality_grade(metrics),
                    "score": metrics.perceived_quality_score,
                    "key_metrics": {
                        "snr": f"{metrics.snr:.1f} dB",
                        "thd": f"{metrics.thd:.2f}%",
                        "dynamic_range": f"{metrics.dynamic_range:.1f} dB",
                        "loudness": f"{metrics.loudness_lufs:.1f} LUFS"
                    }
                }
            }
            
            return result
            
        finally:
            # 清理上传的文件
            if os.path.exists(file_path):
                os.remove(file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传质量分析失败: {file.filename}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/quality-standards")
async def get_quality_standards():
    """获取音频质量标准"""
    return {
        "broadcast_standards": {
            "EBU_R128": {
                "loudness": "-23 LUFS",
                "peak": "-1 dBTP",
                "range": "7-20 LU"
            },
            "ATSC_A85": {
                "loudness": "-24 LUFS",
                "peak": "-2 dBFS"
            }
        },
        "quality_grades": {
            "Excellent": {
                "score_range": "90-100",
                "snr": ">60 dB",
                "thd": "<0.1%",
                "dynamic_range": ">60 dB"
            },
            "Good": {
                "score_range": "75-89",
                "snr": "40-60 dB",
                "thd": "0.1-0.5%",
                "dynamic_range": "40-60 dB"
            },
            "Fair": {
                "score_range": "60-74",
                "snr": "20-40 dB",
                "thd": "0.5-1.0%",
                "dynamic_range": "20-40 dB"
            },
            "Poor": {
                "score_range": "40-59",
                "snr": "10-20 dB",
                "thd": "1.0-3.0%",
                "dynamic_range": "10-20 dB"
            },
            "Very Poor": {
                "score_range": "0-39",
                "snr": "<10 dB",
                "thd": ">3.0%",
                "dynamic_range": "<10 dB"
            }
        },
        "recommended_values": {
            "snr": "信噪比应大于40dB",
            "thd": "总谐波失真应小于1%",
            "dynamic_range": "动态范围应大于20dB",
            "loudness": "响度应在-23 LUFS左右",
            "peak_level": "峰值电平应小于-1dB"
        }
    }


@router.get("/analysis-report/{file_path:path}")
async def generate_analysis_report(file_path: str, format: str = "json"):
    """生成详细的质量分析报告"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="音频文件不存在")
        
        # 执行质量分析
        metrics = global_quality_analyzer.analyze_audio_quality(file_path)
        
        # 生成详细报告
        report = {
            "file_info": {
                "path": file_path,
                "filename": os.path.basename(file_path),
                "size": os.path.getsize(file_path),
                "duration": metrics.duration,
                "sample_rate": metrics.sample_rate,
                "channels": metrics.channels,
                "bit_depth": metrics.bit_depth
            },
            "quality_metrics": _convert_metrics_to_response(metrics).dict(),
            "quality_assessment": {
                "overall_grade": global_quality_analyzer._determine_quality_grade(metrics),
                "overall_score": metrics.perceived_quality_score,
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            },
            "technical_analysis": {
                "frequency_domain": {
                    "spectral_centroid": metrics.spectral_centroid,
                    "spectral_rolloff": metrics.spectral_rolloff,
                    "spectral_bandwidth": metrics.spectral_bandwidth,
                    "frequency_response_flatness": metrics.frequency_response_flatness
                },
                "time_domain": {
                    "zero_crossing_rate": metrics.zero_crossing_rate,
                    "tempo": metrics.tempo,
                    "dynamic_range": metrics.dynamic_range
                },
                "stereo_analysis": {
                    "stereo_width": metrics.stereo_width,
                    "phase_correlation": metrics.phase_correlation
                } if metrics.channels > 1 else None
            }
        }
        
        # 添加优缺点分析
        if metrics.snr > 50:
            report["quality_assessment"]["strengths"].append("优秀的信噪比")
        elif metrics.snr < 30:
            report["quality_assessment"]["weaknesses"].append("信噪比偏低")
        
        if metrics.thd < 0.5:
            report["quality_assessment"]["strengths"].append("低失真")
        elif metrics.thd > 2.0:
            report["quality_assessment"]["weaknesses"].append("失真较高")
        
        if metrics.dynamic_range > 40:
            report["quality_assessment"]["strengths"].append("良好的动态范围")
        elif metrics.dynamic_range < 15:
            report["quality_assessment"]["weaknesses"].append("动态范围不足")
        
        # 添加建议
        if metrics.snr < 40:
            report["quality_assessment"]["recommendations"].append("建议降噪处理")
        if metrics.thd > 1.0:
            report["quality_assessment"]["recommendations"].append("建议检查失真源")
        if metrics.dynamic_range < 20:
            report["quality_assessment"]["recommendations"].append("建议避免过度压缩")
        
        return report
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="音频文件不存在")
    except Exception as e:
        logger.error(f"生成分析报告失败: {file_path}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")
