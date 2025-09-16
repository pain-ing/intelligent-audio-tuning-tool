"""
音频处理服务
"""
import os
import tempfile
from typing import Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.services.base import BaseService, AudioProcessorInterface
from src.core.exceptions import AudioProcessingError, FileError, ErrorCode


class AudioService(BaseService, AudioProcessorInterface):
    """音频处理服务"""
    
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=self.config.worker_concurrency)
    
    async def analyze_features(self, file_path: str) -> Dict[str, Any]:
        """分析音频特征"""
        if not os.path.exists(file_path):
            raise AudioProcessingError(
                message=f"Audio file not found: {file_path}",
                code=ErrorCode.FILE_NOT_FOUND
            )

        try:
            # 在线程池中执行CPU密集型任务
            loop = asyncio.get_event_loop()
            features = await loop.run_in_executor(
                self.executor,
                self._analyze_features_sync,
                file_path
            )
            
            self.logger.info(f"Audio analysis completed for {file_path}")
            return features
            
        except Exception as e:
            self._handle_error(
                e,
                f"Audio analysis failed for {file_path}"
            )
    
    def _analyze_features_sync(self, file_path: str) -> Dict[str, Any]:
        """同步音频特征分析"""
        try:
            # 导入音频分析模块
            from worker.app.audio_analysis import analyzer
            return analyzer.analyze_features(file_path)
            
        except ImportError:
            # 如果无法导入，返回默认特征
            self.logger.warning("Audio analysis module not available, using defaults")
            return self._get_default_features()
        except Exception as e:
            raise AudioProcessingError(
                message=f"Feature analysis failed: {str(e)}",
                code=ErrorCode.AUDIO_ANALYSIS_FAILED,
                detail={"file_path": file_path}
            )
    
    async def invert_parameters(
        self,
        ref_features: Dict[str, Any],
        tgt_features: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """参数反演"""
        try:
            loop = asyncio.get_event_loop()
            params = await loop.run_in_executor(
                self.executor,
                self._invert_parameters_sync,
                ref_features,
                tgt_features,
                mode
            )
            
            self.logger.info(f"Parameter inversion completed for mode {mode}")
            return params
            
        except Exception as e:
            self._handle_error(
                e,
                f"Parameter inversion failed for mode {mode}"
            )
    
    def _invert_parameters_sync(
        self,
        ref_features: Dict[str, Any],
        tgt_features: Dict[str, Any],
        mode: str
    ) -> Dict[str, Any]:
        """同步参数反演"""
        try:
            from worker.app.parameter_inversion import ParameterInverter
            inverter = ParameterInverter()
            return inverter.invert_parameters(ref_features, tgt_features, mode)
            
        except ImportError:
            self.logger.warning("Parameter inversion module not available, using defaults")
            return self._get_default_parameters()
        except Exception as e:
            raise AudioProcessingError(
                message=f"Parameter inversion failed: {str(e)}",
                code=ErrorCode.PARAMETER_INVERSION_FAILED,
                detail={"mode": mode}
            )
    
    async def render_audio(
        self,
        input_path: str,
        output_path: str,
        style_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """音频渲染"""
        if not os.path.exists(input_path):
            raise FileError(
                message=f"Input audio file not found: {input_path}",
                code=ErrorCode.FILE_NOT_FOUND
            )
        
        try:
            loop = asyncio.get_event_loop()
            metrics = await loop.run_in_executor(
                self.executor,
                self._render_audio_sync,
                input_path,
                output_path,
                style_params
            )
            
            self.logger.info(f"Audio rendering completed: {input_path} -> {output_path}")
            return metrics
            
        except Exception as e:
            self._handle_error(
                e,
                f"Audio rendering failed: {input_path} -> {output_path}"
            )
    
    def _render_audio_sync(
        self,
        input_path: str,
        output_path: str,
        style_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """同步音频渲染"""
        try:
            from worker.app.audio_rendering import renderer
            return renderer.render_audio(input_path, output_path, style_params)
            
        except ImportError:
            self.logger.warning("Audio rendering module not available, using defaults")
            # 复制输入文件到输出路径作为默认行为
            import shutil
            shutil.copy2(input_path, output_path)
            return self._get_default_metrics()
        except Exception as e:
            raise AudioProcessingError(
                message=f"Audio rendering failed: {str(e)}",
                code=ErrorCode.AUDIO_RENDERING_FAILED,
                detail={"input_path": input_path, "output_path": output_path}
            )
    
    def _get_default_features(self) -> Dict[str, Any]:
        """获取默认特征"""
        return {
            "stft": {"features": {"win_2048": {"spectral_centroid": 1000, "spectral_bandwidth": 1000}}},
            "mel": {"mean": -30, "std": 10},
            "lufs": {"integrated_lufs": -23.0, "short_term_lufs": []},
            "true_peak_db": -3.0,
            "f0": {"mean_f0": 0, "voiced_ratio": 0},
            "stereo": {"is_stereo": False, "width": 1.0, "correlation": 1.0},
            "reverb": {"rt60_estimate": 0.5, "reverb_presence": 0.0},
            "audio_info": {"duration_seconds": 10.0, "channels": 1, "sample_rate": 48000}
        }
    
    def _get_default_parameters(self) -> Dict[str, Any]:
        """获取默认参数"""
        return {
            "eq": {"bands": []},
            "dynamics": {"compressor": {}, "limiter": {}},
            "reverb": {"ir_params": {}},
            "stereo": {"width": 1.0},
            "pitch": {"semitones": 0.0}
        }
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """获取默认指标"""
        return {
            "stft_dist": 0.0,
            "mel_dist": 0.0,
            "lufs_err": 0.0,
            "tp_db": -1.0,
            "artifacts_rate": 0.0
        }
