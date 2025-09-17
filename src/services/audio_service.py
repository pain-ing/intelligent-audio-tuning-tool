"""
音频处理服务
"""
import os
import tempfile
from typing import Dict, Any, Optional
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from src.services.base import BaseService, AudioProcessorInterface
from src.core.exceptions import AudioProcessingError, FileError, ErrorCode
from src.utils.memory_optimizer import memory_efficient, get_memory_usage


class AudioService(BaseService, AudioProcessorInterface):
    """音频处理服务"""
    
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=self.config.worker_concurrency)
    
    @memory_efficient(max_memory_mb=512.0)
    async def analyze_features(self, file_path: str) -> Dict[str, Any]:
        """分析音频特征（内存优化版本）"""
        if not os.path.exists(file_path):
            raise AudioProcessingError(
                message=f"Audio file not found: {file_path}",
                code=ErrorCode.FILE_NOT_FOUND
            )

        start_time = time.time()
        initial_memory = get_memory_usage()

        try:
            # 在线程池中执行CPU密集型任务
            loop = asyncio.get_event_loop()
            features = await loop.run_in_executor(
                self.executor,
                self._analyze_features_sync,
                file_path
            )

            # 性能监控
            duration = time.time() - start_time
            final_memory = get_memory_usage()
            memory_used = final_memory.get('process_rss_mb', 0) - initial_memory.get('process_rss_mb', 0)

            self.logger.info(
                f"Audio analysis completed for {file_path} - "
                f"Duration: {duration:.2f}s, Memory used: {memory_used:.1f}MB"
            )
            return features

        except Exception as e:
            self._handle_error(
                e,
                f"Audio analysis failed for {file_path}"
            )
    
    def _analyze_features_sync(self, file_path: str) -> Dict[str, Any]:
        """同步音频特征分析（内存优化版本）"""
        try:
            # 导入音频分析模块
            from worker.app.audio_analysis import analyzer

            # 检查文件大小，大文件使用流式处理
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            if file_size_mb > 50:  # 大于50MB使用流式处理
                self.logger.info(f"Large file detected ({file_size_mb:.1f}MB), using streaming analysis")
                return analyzer.analyze_features_streaming(file_path)
            else:
                return analyzer.analyze_features(file_path)

        except ImportError:
            # 如果无法导入，返回默认特征
            self.logger.warning("Audio analysis module not available, using defaults")
            return self._get_default_features()
        except Exception as e:
            raise AudioProcessingError(
                message=f"Feature analysis failed: {str(e)}",
                code=ErrorCode.AUDIO_ANALYSIS_FAILED,
                detail={"file_path": file_path, "file_size_mb": file_size_mb if 'file_size_mb' in locals() else 0}
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
