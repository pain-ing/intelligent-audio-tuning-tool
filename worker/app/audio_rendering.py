"""
音频渲染模块 - 将风格参数应用到目标音频
"""

import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln
from typing import Dict, Tuple, Optional
import logging
from scipy import signal
from pedalboard import Pedalboard, Compressor, Limiter, Reverb, Gain, HighpassFilter, LowpassFilter, PeakFilter
import tempfile
import os

logger = logging.getLogger(__name__)

class AudioRenderer:
    """音频渲染器"""
    
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.meter = pyln.Meter(sample_rate)
        
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """加载音频文件"""
        try:
            audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=False)
            
            if audio.ndim == 1:
                audio = audio.reshape(1, -1)
            elif audio.ndim == 2 and audio.shape[0] > audio.shape[1]:
                audio = audio.T
                
            logger.info(f"Loaded audio for rendering: {audio.shape} at {sr}Hz")
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
                         chunk_duration: float = 30.0) -> np.ndarray:
        """分块处理长音频"""
        chunk_samples = int(chunk_duration * self.sample_rate)
        
        if audio.shape[1] <= chunk_samples:
            # 音频较短，直接处理
            return self.apply_style_params(audio, style_params)
        
        # 分块处理
        processed_chunks = []
        overlap_samples = int(0.1 * self.sample_rate)  # 100ms 重叠
        
        for start in range(0, audio.shape[1], chunk_samples - overlap_samples):
            end = min(start + chunk_samples, audio.shape[1])
            chunk = audio[:, start:end]
            
            # 处理块
            processed_chunk = self.apply_style_params(chunk, style_params)
            
            # 处理重叠区域
            if start > 0 and len(processed_chunks) > 0:
                # 交叉淡化重叠区域
                fade_samples = min(overlap_samples, processed_chunk.shape[1] // 2)
                
                # 前一块的尾部淡出
                prev_chunk = processed_chunks[-1]
                if prev_chunk.shape[1] > fade_samples:
                    fade_out = np.linspace(1, 0, fade_samples)
                    prev_chunk[:, -fade_samples:] *= fade_out
                
                # 当前块的头部淡入
                if processed_chunk.shape[1] > fade_samples:
                    fade_in = np.linspace(0, 1, fade_samples)
                    processed_chunk[:, :fade_samples] *= fade_in
                    
                    # 混合重叠区域
                    if prev_chunk.shape[1] >= fade_samples:
                        processed_chunk[:, :fade_samples] += prev_chunk[:, -fade_samples:]
                        prev_chunk = prev_chunk[:, :-fade_samples]
                        processed_chunks[-1] = prev_chunk
            
            processed_chunks.append(processed_chunk)
        
        # 拼接所有块
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
    
    def render_audio(self, input_path: str, output_path: str, style_params: Dict) -> Dict:
        """主要的音频渲染函数"""
        logger.info(f"Starting audio rendering: {input_path} -> {output_path}")
        
        try:
            # 加载音频
            audio, sr = self.load_audio(input_path)
            
            # 应用风格参数
            processed_audio = self.process_in_chunks(audio, style_params)
            
            # 保存结果
            self.save_audio(processed_audio, output_path, sr)
            
            # 计算质量指标
            metrics = self.calculate_metrics(audio, processed_audio, style_params)
            
            logger.info("Audio rendering completed successfully")
            return metrics
            
        except Exception as e:
            logger.error(f"Audio rendering failed: {e}")
            raise
    
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

# 全局渲染器实例
renderer = AudioRenderer()
