"""
音频渲染模块 - 将风格参数应用到目标音频（内存优化版本）
"""

import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln
from typing import Dict, Tuple, Optional
import logging
import time
from scipy import signal
from pedalboard import Pedalboard, Compressor, Limiter, Reverb, Gain, HighpassFilter, LowpassFilter, PeakFilter
import tempfile
import os
import gc

# 导入流式处理模块
from .audio_streaming import MemoryAwareAudioLoader, AudioChunk, StreamingAudioProcessor

# 导入Adobe Audition渲染器
try:
    from .audition_renderer import AuditionAudioRenderer, create_audition_renderer
    from .audition_error_handler import global_error_handler, ErrorSeverity, RecoveryStrategy
    from .performance_monitor import global_performance_monitor
    AUDITION_AVAILABLE = True
except ImportError:
    AUDITION_AVAILABLE = False
    AuditionAudioRenderer = None

logger = logging.getLogger(__name__)

class AudioRenderer:
    """音频渲染器（内存优化版本）"""

    def __init__(self, sample_rate: int = 48000, max_memory_mb: float = 512.0, renderer_type: str = "default"):
        self.sample_rate = sample_rate
        self.meter = pyln.Meter(sample_rate)
        self.max_memory_mb = max_memory_mb
        self.renderer_type = renderer_type

        # 内存优化：使用 float32
        self.dtype = np.float32

        # 流式处理器
        self.streaming_processor = StreamingAudioProcessor(max_memory_mb=max_memory_mb)

        # 自适应分块参数
        self._adaptive_chunk_size = self._calculate_adaptive_chunk_size()

        # 初始化Adobe Audition渲染器（如果可用且被选择）
        self.audition_renderer = None
        if renderer_type == "audition" and AUDITION_AVAILABLE:
            try:
                self.audition_renderer = AuditionAudioRenderer()
                if not self.audition_renderer.is_audition_available():
                    logger.warning("Adobe Audition不可用，回退到默认渲染器")
                    self.audition_renderer = None
                    self.renderer_type = "default"
                else:
                    logger.info("Adobe Audition渲染器初始化成功")
            except Exception as e:
                logger.error(f"Adobe Audition渲染器初始化失败: {e}")
                self.audition_renderer = None
                self.renderer_type = "default"

    def _calculate_adaptive_chunk_size(self) -> int:
        """根据可用内存计算自适应分块大小"""
        try:
            import psutil
            # 获取可用内存（GB）
            available_memory_gb = psutil.virtual_memory().available / (1024**3)

            # 根据可用内存调整分块大小
            if available_memory_gb > 8:
                chunk_duration = 60.0  # 8GB+ 内存：60秒块
            elif available_memory_gb > 4:
                chunk_duration = 30.0  # 4-8GB 内存：30秒块
            else:
                chunk_duration = 15.0  # <4GB 内存：15秒块

            return int(chunk_duration * self.sample_rate)

        except ImportError:
            # 如果没有 psutil，使用默认值
            return int(30.0 * self.sample_rate)  # 30秒默认
        
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """加载音频文件"""
        try:
            # 使用 librosa 加载音频，指定 dtype 为 float32
            audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=False, dtype=self.dtype)

            if audio.ndim == 1:
                audio = audio.reshape(1, -1)
            elif audio.ndim == 2 and audio.shape[0] > audio.shape[1]:
                audio = audio.T

            # 确保数据类型为 float32
            audio = audio.astype(self.dtype)

            logger.info(f"Loaded audio for rendering: {audio.shape} at {sr}Hz, dtype: {audio.dtype}")
            return audio, sr
            
        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {e}")
            raise
    
    def save_audio(self, audio: np.ndarray, output_path: str, sample_rate: int = None):
        """保存音频文件"""
        if sample_rate is None:
            sample_rate = self.sample_rate
            
        try:
            # 确保音频在合理范围内
            audio = np.clip(audio, -1.0, 1.0)
            
            # 转换为正确的形状 (samples, channels)
            if audio.ndim == 2:
                audio = audio.T
            
            sf.write(output_path, audio, sample_rate, subtype='PCM_24')
            logger.info(f"Saved rendered audio to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save audio to {output_path}: {e}")
            raise
    
    def apply_eq(self, audio: np.ndarray, eq_params: list) -> np.ndarray:
        """应用均衡器"""
        if not eq_params:
            return audio
        
        try:
            # 创建 Pedalboard 效果链
            board = Pedalboard()
            
            for eq in eq_params:
                freq = eq.get("f_hz", 1000)
                gain = eq.get("gain_db", 0)
                q = eq.get("q", 1.0)
                eq_type = eq.get("type", "peaking")
                
                if abs(gain) < 0.1:  # 跳过微小的调整
                    continue
                
                if eq_type == "peaking":
                    board.append(PeakFilter(cutoff_frequency_hz=freq, gain_db=gain, q=q))
                elif eq_type == "highpass":
                    board.append(HighpassFilter(cutoff_frequency_hz=freq))
                elif eq_type == "lowpass":
                    board.append(LowpassFilter(cutoff_frequency_hz=freq))
            
            # 应用效果
            if len(board) > 0:
                processed = board(audio.T, sample_rate=self.sample_rate)
                return processed.T
            else:
                return audio
                
        except Exception as e:
            logger.warning(f"EQ processing failed: {e}")
            return audio
    
    def apply_compression(self, audio: np.ndarray, comp_params: Dict) -> np.ndarray:
        """应用压缩"""
        if not comp_params.get("enabled", False):
            return audio
        
        try:
            threshold = comp_params.get("threshold_db", -20)
            ratio = comp_params.get("ratio", 2.0)
            attack_ms = comp_params.get("attack_ms", 10.0)
            release_ms = comp_params.get("release_ms", 100.0)
            
            compressor = Compressor(
                threshold_db=threshold,
                ratio=ratio,
                attack_ms=attack_ms,
                release_ms=release_ms
            )
            
            processed = compressor(audio.T, sample_rate=self.sample_rate)
            return processed.T
            
        except Exception as e:
            logger.warning(f"Compression failed: {e}")
            return audio
    
    def apply_reverb(self, audio: np.ndarray, reverb_params: Dict) -> np.ndarray:
        """应用混响"""
        mix_level = reverb_params.get("mix", 0.0)
        
        if mix_level < 0.01:  # 跳过微小的混响
            return audio
        
        try:
            # 使用 Pedalboard 的内置混响
            reverb = Reverb(
                room_size=min(1.0, mix_level * 2),
                damping=0.5,
                wet_level=mix_level,
                dry_level=1.0 - mix_level * 0.5,
                width=1.0
            )
            
            processed = reverb(audio.T, sample_rate=self.sample_rate)
            return processed.T
            
        except Exception as e:
            logger.warning(f"Reverb processing failed: {e}")
            return audio
    
    def apply_stereo_width(self, audio: np.ndarray, stereo_params: Dict) -> np.ndarray:
        """应用立体声宽度调整"""
        width = stereo_params.get("width", 1.0)
        
        if abs(width - 1.0) < 0.05 or audio.shape[0] < 2:  # 跳过微小调整或单声道
            return audio
        
        try:
            left = audio[0]
            right = audio[1] if audio.shape[0] > 1 else audio[0]
            
            # M/S 处理
            mid = (left + right) / 2
            side = (left - right) / 2
            
            # 调整宽度
            side = side * width
            
            # 转换回 L/R
            new_left = mid + side
            new_right = mid - side
            
            # 防止削波
            max_val = max(np.max(np.abs(new_left)), np.max(np.abs(new_right)))
            if max_val > 0.95:
                scale = 0.95 / max_val
                new_left *= scale
                new_right *= scale
            
            return np.array([new_left, new_right])
            
        except Exception as e:
            logger.warning(f"Stereo width processing failed: {e}")
            return audio
    
    def apply_pitch_shift(self, audio: np.ndarray, pitch_params: Dict) -> np.ndarray:
        """应用音高调整"""
        semitones = pitch_params.get("semitones", 0.0)
        
        if abs(semitones) < 0.1:  # 跳过微小的调整
            return audio
        
        try:
            # 使用 librosa 进行音高调整
            processed_channels = []
            
            for channel in range(audio.shape[0]):
                shifted = librosa.effects.pitch_shift(
                    audio[channel], 
                    sr=self.sample_rate, 
                    n_steps=semitones
                )
                processed_channels.append(shifted)
            
            return np.array(processed_channels)
            
        except Exception as e:
            logger.warning(f"Pitch shift failed: {e}")
            return audio
    
    def apply_lufs_normalization(self, audio: np.ndarray, lufs_params: Dict) -> np.ndarray:
        """应用 LUFS 响度归一化"""
        target_lufs = lufs_params.get("target_lufs", -23.0)
        
        try:
            # 转换为单声道用于测量
            if audio.shape[0] == 1:
                audio_mono = audio[0]
            else:
                audio_mono = np.mean(audio, axis=0)
            
            # 测量当前响度
            current_lufs = self.meter.integrated_loudness(audio_mono)
            
            if np.isnan(current_lufs) or np.isinf(current_lufs):
                logger.warning("Invalid LUFS measurement, skipping normalization")
                return audio
            
            # 计算增益
            gain_db = target_lufs - current_lufs
            gain_db = np.clip(gain_db, -20, 20)  # 限制增益范围
            
            if abs(gain_db) > 0.1:
                gain_linear = 10 ** (gain_db / 20)
                audio = audio * gain_linear
                logger.info(f"Applied LUFS normalization: {gain_db:.1f}dB")
            
            return audio
            
        except Exception as e:
            logger.warning(f"LUFS normalization failed: {e}")
            return audio
    
    def apply_limiter(self, audio: np.ndarray, limiter_params: Dict) -> np.ndarray:
        """应用限制器"""
        try:
            threshold_db = limiter_params.get("tp_db", -1.0)
            release_ms = limiter_params.get("release_ms", 100.0)
            
            limiter = Limiter(
                threshold_db=threshold_db,
                release_ms=release_ms
            )
            
            processed = limiter(audio.T, sample_rate=self.sample_rate)
            return processed.T
            
        except Exception as e:
            logger.warning(f"Limiter processing failed: {e}")
            return audio
    
    def process_in_chunks(self, audio: np.ndarray, style_params: Dict,
                         chunk_duration: float = None) -> np.ndarray:
        """分块处理长音频（自适应内存优化 + 可选并行）"""
        # 使用自适应分块大小，如果未指定则使用计算的值
        if chunk_duration is None:
            chunk_samples = self._adaptive_chunk_size
        else:
            chunk_samples = int(chunk_duration * self.sample_rate)

        if audio.shape[1] <= chunk_samples:
            # 音频较短，直接处理
            return self.apply_style_params(audio, style_params)

        # 预切分块范围
        overlap_samples = int(0.1 * self.sample_rate)  # 100ms 重叠
        step = max(1, chunk_samples - overlap_samples)
        ranges = []
        for start in range(0, audio.shape[1], step):
            end = min(start + chunk_samples, audio.shape[1])
            ranges.append((start, end))
            if end == audio.shape[1]:
                break

        # 并发度（默认1 = 顺序执行）
        try:
            max_workers = int(os.getenv("RENDER_MAX_WORKERS", "1"))
        except Exception:
            max_workers = 1
        max_workers = max(1, min(max_workers, 8))  # 安全上限

        # 处理函数
        def _process_range(rng):
            s, e = rng
            chunk = audio[:, s:e]
            return s, e, self.apply_style_params(chunk, style_params)

        # 并行或顺序处理
        results = []
        if max_workers > 1:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = [ex.submit(_process_range, rng) for rng in ranges]
                for fut in as_completed(futs):
                    results.append(fut.result())
            # 恢复时间顺序
            results.sort(key=lambda x: x[0])
        else:
            for rng in ranges:
                results.append(_process_range(rng))

        # 按顺序做重叠交叉淡化并拼接
        processed_chunks = []
        for idx, (s, e, processed_chunk) in enumerate(results):
            if idx > 0 and len(processed_chunks) > 0:
                fade_samples = min(overlap_samples, processed_chunk.shape[1] // 2)
                prev_chunk = processed_chunks[-1]
                if prev_chunk.shape[1] > fade_samples:
                    fade_out = np.linspace(1, 0, fade_samples)
                    prev_chunk[:, -fade_samples:] *= fade_out
                if processed_chunk.shape[1] > fade_samples:
                    fade_in = np.linspace(0, 1, fade_samples)
                    processed_chunk[:, :fade_samples] *= fade_in
                    if prev_chunk.shape[1] >= fade_samples:
                        processed_chunk[:, :fade_samples] += prev_chunk[:, -fade_samples:]
                        prev_chunk = prev_chunk[:, :-fade_samples]
                        processed_chunks[-1] = prev_chunk
            processed_chunks.append(processed_chunk)

        return np.concatenate(processed_chunks, axis=1)
    
    def apply_style_params(self, audio: np.ndarray, style_params: Dict) -> np.ndarray:
        """应用完整的风格参数链"""
        logger.info("Applying style parameters")
        
        # 获取处理链顺序
        processing_chain = style_params.get("metadata", {}).get("processing_chain", 
                                                               ["eq", "compression", "reverb", "stereo", "pitch", "lufs", "limiter"])
        
        processed_audio = audio.copy()
        
        for step in processing_chain:
            if step == "eq" and "eq" in style_params:
                processed_audio = self.apply_eq(processed_audio, style_params["eq"])
            elif step == "compression" and "compression" in style_params:
                processed_audio = self.apply_compression(processed_audio, style_params["compression"])
            elif step == "reverb" and "reverb" in style_params:
                processed_audio = self.apply_reverb(processed_audio, style_params["reverb"])
            elif step == "stereo" and "stereo" in style_params:
                processed_audio = self.apply_stereo_width(processed_audio, style_params["stereo"])
            elif step == "pitch" and "pitch" in style_params:
                processed_audio = self.apply_pitch_shift(processed_audio, style_params["pitch"])
            elif step == "lufs" and "lufs" in style_params:
                processed_audio = self.apply_lufs_normalization(processed_audio, style_params["lufs"])
            elif step == "limiter" and "limiter" in style_params:
                processed_audio = self.apply_limiter(processed_audio, style_params["limiter"])
        
        logger.info("Style parameters applied successfully")
        return processed_audio
    
    def render_audio(self, input_path: str, output_path: str, style_params: Dict,
                    use_streaming: bool = None) -> Dict:
        """主要的音频渲染函数（支持流式处理和Adobe Audition）"""
        logger.info(f"Starting audio rendering: {input_path} -> {output_path}")

        # 生成会话ID
        import uuid
        session_id = f"render_{uuid.uuid4().hex[:8]}"

        # 获取输入文件大小
        input_size = 0
        try:
            input_size = os.path.getsize(input_path)
        except OSError:
            pass

        # 使用性能监控
        with global_performance_monitor.monitor_session(
            session_id=session_id,
            operation_type="audio_rendering",
            renderer_type=self.renderer_type,
            input_path=input_path,
            output_path=output_path,
            input_size=input_size,
            style_params_count=len(style_params)
        ) as session:

            session.input_size = input_size

            start_time = time.time()
            context = {
                "input_path": input_path,
                "output_path": output_path,
                "renderer_type": self.renderer_type,
                "style_params": style_params,
                "session_id": session_id
            }

            try:
                # 如果使用Adobe Audition渲染器
                if self.renderer_type == "audition" and self.audition_renderer:
                    logger.info("使用Adobe Audition进行音频渲染")

                    # 使用熔断器保护Adobe Audition调用
                    circuit_breaker = global_error_handler.get_circuit_breaker("audition_renderer")

                    try:
                        result = circuit_breaker.call(
                            self.audition_renderer.render_audio,
                            input_path, output_path, style_params
                        )

                        # 更新会话输出大小
                        try:
                            session.output_size = os.path.getsize(output_path)
                        except OSError:
                            pass

                        return result

                    except Exception as audition_error:
                        # 处理Adobe Audition错误
                        error_context = global_error_handler.handle_error(
                            audition_error, "audition_rendering", context
                        )

                        # 根据恢复策略决定下一步
                        if error_context.recovery_strategy == RecoveryStrategy.FALLBACK:
                            logger.warning("Adobe Audition渲染失败，回退到默认渲染器")
                            self.renderer_type = "default"
                            self.audition_renderer = None
                            # 继续使用默认渲染器
                        else:
                            raise

                # 决定是否使用流式处理
                if use_streaming is None:
                    file_size_mb = input_size / (1024 * 1024)
                    use_streaming = file_size_mb > 30  # 大于30MB使用流式处理

                # 使用默认渲染器
                if use_streaming:
                    logger.info("使用流式处理进行音频渲染")
                    result = self._render_audio_streaming_with_error_handling(
                        input_path, output_path, style_params, context
                    )
                else:
                    logger.info("使用传统方式进行音频渲染")
                    result = self._render_audio_traditional_with_error_handling(
                        input_path, output_path, style_params, context
                    )

                # 更新会话输出大小
                try:
                    session.output_size = os.path.getsize(output_path)
                except OSError:
                    pass

                # 添加性能指标到结果
                processing_time = time.time() - start_time
                result["processing_time"] = processing_time
                result["session_id"] = session_id

                return result

            except Exception as e:
                # 全局错误处理
                processing_time = time.time() - start_time
                context["processing_time"] = processing_time

                error_context = global_error_handler.handle_error(
                    e, "audio_rendering", context
                )

                logger.error(f"Audio rendering failed after {processing_time:.2f}s: {e}")

                # 根据错误严重程度决定是否重新抛出
                if error_context.severity == ErrorSeverity.CRITICAL:
                    raise
                else:
                    # 返回默认指标，避免完全失败
                    result = self._get_default_metrics()
                    result["processing_time"] = processing_time
                    result["session_id"] = session_id
                    return result

    def _render_audio_traditional(self, input_path: str, output_path: str, style_params: Dict) -> Dict:
        """传统的音频渲染方法"""
        # 加载音频
        audio, sr = self.load_audio(input_path)

        # 应用风格参数
        processed_audio = self.process_in_chunks(audio, style_params)

        # 保存结果
        self.save_audio(processed_audio, output_path, sr)

        # 计算质量指标
        metrics = self.calculate_metrics(audio, processed_audio, style_params)

        logger.info("Traditional audio rendering completed successfully")
        return metrics

    def _render_audio_traditional_with_error_handling(self,
                                                    input_path: str,
                                                    output_path: str,
                                                    style_params: Dict,
                                                    context: Dict) -> Dict:
        """带错误处理的传统音频渲染方法"""
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                return self._render_audio_traditional(input_path, output_path, style_params)
            except MemoryError as e:
                error_context = global_error_handler.handle_error(
                    e, "memory_error", {**context, "attempt": attempt}
                )

                if attempt < max_retries - 1:
                    logger.warning(f"内存错误，尝试 {attempt + 1}/{max_retries}，清理内存后重试")
                    # 强制垃圾回收
                    import gc
                    gc.collect()
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    # 最后一次尝试失败，尝试降级处理
                    logger.warning("内存不足，尝试降级处理")
                    return self._render_audio_degraded(input_path, output_path, style_params)
            except Exception as e:
                error_context = global_error_handler.handle_error(
                    e, "traditional_rendering", {**context, "attempt": attempt}
                )

                if attempt < max_retries - 1 and error_context.recovery_strategy == RecoveryStrategy.RETRY:
                    logger.warning(f"渲染失败，尝试 {attempt + 1}/{max_retries}，重试中...")
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise

        raise RuntimeError("所有重试尝试都失败了")

    def _render_audio_streaming_with_error_handling(self,
                                                  input_path: str,
                                                  output_path: str,
                                                  style_params: Dict,
                                                  context: Dict) -> Dict:
        """带错误处理的流式音频渲染方法"""
        try:
            return self._render_audio_streaming(input_path, output_path, style_params)
        except Exception as e:
            error_context = global_error_handler.handle_error(
                e, "streaming_rendering", context
            )

            if error_context.recovery_strategy == RecoveryStrategy.FALLBACK:
                logger.warning("流式处理失败，回退到传统处理")
                return self._render_audio_traditional_with_error_handling(
                    input_path, output_path, style_params, context
                )
            else:
                raise

    def _render_audio_degraded(self, input_path: str, output_path: str, style_params: Dict) -> Dict:
        """降级音频渲染（简化处理以节省内存）"""
        logger.info("使用降级模式进行音频渲染")

        try:
            # 使用更小的块大小
            original_chunk_size = self._adaptive_chunk_size
            self._adaptive_chunk_size = min(self._adaptive_chunk_size // 4, 48000)  # 最小1秒

            # 简化风格参数
            simplified_params = self._simplify_style_params(style_params)

            # 执行简化处理
            result = self._render_audio_traditional(input_path, output_path, simplified_params)

            # 恢复原始块大小
            self._adaptive_chunk_size = original_chunk_size

            # 标记为降级处理
            result["degraded_processing"] = True
            result["original_params_count"] = len(style_params)
            result["simplified_params_count"] = len(simplified_params)

            logger.info("降级音频渲染完成")
            return result

        except Exception as e:
            logger.error(f"降级渲染也失败了: {e}")
            # 返回最基本的处理结果
            return self._copy_file_with_basic_processing(input_path, output_path)

    def _simplify_style_params(self, style_params: Dict) -> Dict:
        """简化风格参数以减少内存使用"""
        simplified = {}

        # 只保留最重要的效果
        priority_effects = ["eq", "compression", "limiter"]

        for effect in priority_effects:
            if effect in style_params:
                if effect == "eq" and "bands" in style_params[effect]:
                    # 限制EQ频段数量
                    bands = style_params[effect]["bands"][:3]  # 最多3个频段
                    simplified[effect] = {"bands": bands}
                else:
                    simplified[effect] = style_params[effect]

        return simplified

    def _copy_file_with_basic_processing(self, input_path: str, output_path: str) -> Dict:
        """最基本的文件处理（几乎只是复制）"""
        logger.warning("执行最基本的音频处理")

        try:
            import shutil
            shutil.copy2(input_path, output_path)

            return {
                "stft_dist": 0.0,
                "mel_dist": 0.0,
                "lufs_err": 0.0,
                "tp_db": -1.0,
                "artifacts_rate": 0.0,
                "emergency_fallback": True
            }
        except Exception as e:
            logger.error(f"基本文件处理失败: {e}")
            raise

    def _get_default_metrics(self) -> Dict:
        """获取默认指标"""
        return {
            "stft_dist": 0.0,
            "mel_dist": 0.0,
            "lufs_err": 0.0,
            "tp_db": -1.0,
            "artifacts_rate": 0.0,
            "error_fallback": True
        }

    def _render_audio_streaming(self, input_path: str, output_path: str, style_params: Dict) -> Dict:
        """流式音频渲染方法"""
        logger.info("开始流式音频渲染")

        # 创建处理函数
        def chunk_processor(chunk: AudioChunk, **kwargs) -> np.ndarray:
            return self.apply_style_params(chunk.data, kwargs['style_params'])

        # 使用流式处理器
        result = self.streaming_processor.process_audio_streaming(
            input_path,
            chunk_processor,
            output_path,
            style_params=style_params
        )

        # 计算简化的质量指标
        metrics = self._calculate_streaming_metrics(input_path, output_path, style_params)

        logger.info("Streaming audio rendering completed successfully")
        return metrics

    def _calculate_streaming_metrics(self, input_path: str, output_path: str, style_params: Dict) -> Dict:
        """计算流式处理的质量指标"""
        try:
            # 简化的指标计算，避免加载整个文件
            input_info = sf.info(input_path)
            output_info = sf.info(output_path)

            # 基本指标
            metrics = {
                "input_duration": input_info.duration,
                "output_duration": output_info.duration,
                "sample_rate": output_info.samplerate,
                "channels": output_info.channels,
                "processing_mode": "streaming"
            }

            # 如果文件不太大，计算更详细的指标
            if output_info.frames * output_info.channels * 4 < 100 * 1024 * 1024:  # 小于100MB
                try:
                    # 加载小段音频进行质量评估
                    input_sample, _ = librosa.load(input_path, sr=self.sample_rate,
                                                 duration=10.0, dtype=self.dtype)
                    output_sample, _ = librosa.load(output_path, sr=self.sample_rate,
                                                  duration=10.0, dtype=self.dtype)

                    if input_sample.ndim == 1:
                        input_sample = input_sample.reshape(1, -1)
                    if output_sample.ndim == 1:
                        output_sample = output_sample.reshape(1, -1)

                    # 计算简化指标
                    lufs_target = style_params.get('lufs', {}).get('target_lufs', -23.0)
                    output_lufs = self.meter.integrated_loudness(np.mean(output_sample, axis=0))

                    metrics.update({
                        "lufs_err": abs(lufs_target - output_lufs) if not np.isnan(output_lufs) else 0.0,
                        "tp_db": float(20 * np.log10(np.max(np.abs(output_sample)) + 1e-10)),
                        "sample_based": True
                    })

                except Exception as e:
                    logger.warning(f"无法计算详细指标: {e}")
                    metrics.update({
                        "lufs_err": 0.0,
                        "tp_db": -6.0,
                        "sample_based": False
                    })
            else:
                metrics.update({
                    "lufs_err": 0.0,
                    "tp_db": -6.0,
                    "sample_based": False
                })

            return metrics

        except Exception as e:
            logger.error(f"计算流式指标失败: {e}")
            return {
                "processing_mode": "streaming",
                "error": str(e)
            }
    
    def calculate_metrics(self, original: np.ndarray, processed: np.ndarray, style_params: Dict) -> Dict:
        """计算处理质量指标"""
        try:
            # 确保长度一致
            min_length = min(original.shape[1], processed.shape[1])
            orig_trim = original[:, :min_length]
            proc_trim = processed[:, :min_length]
            
            # 计算 STFT 距离
            orig_stft = np.abs(librosa.stft(orig_trim[0]))
            proc_stft = np.abs(librosa.stft(proc_trim[0]))
            stft_dist = np.mean((orig_stft - proc_stft) ** 2)
            
            # 计算 Mel 距离
            orig_mel = librosa.feature.melspectrogram(y=orig_trim[0], sr=self.sample_rate)
            proc_mel = librosa.feature.melspectrogram(y=proc_trim[0], sr=self.sample_rate)
            mel_dist = np.mean((orig_mel - proc_mel) ** 2)
            
            # 计算 LUFS 误差
            orig_mono = orig_trim[0] if orig_trim.shape[0] == 1 else np.mean(orig_trim, axis=0)
            proc_mono = proc_trim[0] if proc_trim.shape[0] == 1 else np.mean(proc_trim, axis=0)
            
            try:
                orig_lufs = self.meter.integrated_loudness(orig_mono)
                proc_lufs = self.meter.integrated_loudness(proc_mono)
                lufs_err = abs(orig_lufs - proc_lufs) if not (np.isnan(orig_lufs) or np.isnan(proc_lufs)) else 0.0
            except:
                lufs_err = 0.0
            
            # 计算真峰值
            proc_peak = np.max(np.abs(proc_trim))
            tp_db = 20 * np.log10(proc_peak) if proc_peak > 0 else -60.0
            
            # 计算失真率 (简化)
            artifacts_rate = min(1.0, np.mean(np.abs(proc_trim) > 0.99))
            
            return {
                "stft_dist": float(stft_dist),
                "mel_dist": float(mel_dist),
                "lufs_err": float(lufs_err),
                "tp_db": float(tp_db),
                "artifacts_rate": float(artifacts_rate)
            }
            
        except Exception as e:
            logger.warning(f"Metrics calculation failed: {e}")
            return {
                "stft_dist": 0.0,
                "mel_dist": 0.0,
                "lufs_err": 0.0,
                "tp_db": -1.0,
                "artifacts_rate": 0.0
            }

# 渲染器工厂函数
def create_audio_renderer(renderer_type: str = "default", **kwargs) -> AudioRenderer:
    """
    创建音频渲染器实例

    Args:
        renderer_type: 渲染器类型 ("default", "audition")
        **kwargs: 其他参数

    Returns:
        AudioRenderer实例
    """
    return AudioRenderer(renderer_type=renderer_type, **kwargs)

# 全局渲染器实例（默认）
renderer = AudioRenderer()
