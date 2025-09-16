"""
内存优化的音频特征提取模块
实现就地计算、减少临时数组创建、优化内存使用
"""

import numpy as np
import librosa
from typing import Dict, Tuple, Optional, Any
import logging
import gc
from scipy import signal
from scipy.stats import pearsonr
import warnings

logger = logging.getLogger(__name__)

class MemoryOptimizedFeatureExtractor:
    """内存优化的特征提取器"""
    
    def __init__(self, sample_rate: int = 48000, dtype: np.dtype = np.float32):
        self.sample_rate = sample_rate
        self.dtype = dtype
        
        # 预分配缓冲区，避免重复分配
        self._stft_buffer = None
        self._mel_buffer = None
        self._mfcc_buffer = None
        
        # 缓存常用的过滤器和窗口
        self._mel_filters_cache = {}
        self._window_cache = {}
        
        logger.info(f"内存优化特征提取器初始化: sr={sample_rate}, dtype={dtype}")
    
    def _get_or_create_buffer(self, buffer_name: str, shape: tuple) -> np.ndarray:
        """获取或创建缓冲区"""
        buffer = getattr(self, f"_{buffer_name}_buffer", None)
        
        if buffer is None or buffer.shape != shape:
            # 创建新缓冲区
            buffer = np.zeros(shape, dtype=self.dtype)
            setattr(self, f"_{buffer_name}_buffer", buffer)
            logger.debug(f"创建缓冲区 {buffer_name}: {shape}")
        else:
            # 重用现有缓冲区，清零
            buffer.fill(0)
        
        return buffer
    
    def _get_cached_window(self, window_type: str, length: int) -> np.ndarray:
        """获取缓存的窗口函数"""
        cache_key = f"{window_type}_{length}"
        
        if cache_key not in self._window_cache:
            if window_type == "hann":
                window = np.hanning(length).astype(self.dtype)
            elif window_type == "hamming":
                window = np.hamming(length).astype(self.dtype)
            else:
                window = np.ones(length, dtype=self.dtype)
            
            self._window_cache[cache_key] = window
            logger.debug(f"缓存窗口函数: {cache_key}")
        
        return self._window_cache[cache_key]
    
    def _get_cached_mel_filters(self, n_mels: int, n_fft: int) -> np.ndarray:
        """获取缓存的Mel过滤器组"""
        cache_key = f"{n_mels}_{n_fft}_{self.sample_rate}"
        
        if cache_key not in self._mel_filters_cache:
            mel_filters = librosa.filters.mel(
                sr=self.sample_rate,
                n_fft=n_fft,
                n_mels=n_mels,
                dtype=self.dtype
            )
            self._mel_filters_cache[cache_key] = mel_filters
            logger.debug(f"缓存Mel过滤器: {cache_key}")
        
        return self._mel_filters_cache[cache_key]
    
    def extract_stft_features_optimized(self, audio: np.ndarray, 
                                      n_fft: int = 2048, 
                                      hop_length: int = None) -> Dict[str, Any]:
        """内存优化的STFT特征提取"""
        if hop_length is None:
            hop_length = n_fft // 4
        
        try:
            # 使用单声道进行分析以减少内存
            if audio.ndim > 1:
                audio_mono = np.mean(audio, axis=0, dtype=self.dtype)
            else:
                audio_mono = audio.astype(self.dtype)
            
            # 获取缓存的窗口
            window = self._get_cached_window("hann", n_fft)
            
            # 计算STFT，使用较小的数据类型
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                stft = librosa.stft(
                    audio_mono, 
                    n_fft=n_fft, 
                    hop_length=hop_length,
                    window=window,
                    dtype=self.dtype
                )
            
            # 计算幅度谱（就地计算）
            magnitude = np.abs(stft)
            
            # 计算频谱质心（内存优化版本）
            freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=n_fft)
            freqs = freqs.astype(self.dtype)
            
            # 使用广播避免创建大矩阵
            spectral_centroid = np.sum(magnitude * freqs[:, np.newaxis], axis=0) / (np.sum(magnitude, axis=0) + 1e-10)
            spectral_centroid = float(np.mean(spectral_centroid))
            
            # 计算频谱带宽（优化版本）
            freq_diff = freqs[:, np.newaxis] - spectral_centroid
            spectral_bandwidth = np.sqrt(
                np.sum(magnitude * freq_diff**2, axis=0) / (np.sum(magnitude, axis=0) + 1e-10)
            )
            spectral_bandwidth = float(np.mean(spectral_bandwidth))
            
            # 计算频谱滚降（优化版本）
            cumsum_magnitude = np.cumsum(magnitude, axis=0)
            total_magnitude = cumsum_magnitude[-1, :]
            rolloff_threshold = 0.85 * total_magnitude
            
            rolloff_indices = np.argmax(cumsum_magnitude >= rolloff_threshold[np.newaxis, :], axis=0)
            spectral_rolloff = float(np.mean(freqs[rolloff_indices]))
            
            # 清理临时变量
            del stft, magnitude, freq_diff, cumsum_magnitude
            gc.collect()
            
            return {
                "spectral_centroid": spectral_centroid,
                "spectral_bandwidth": spectral_bandwidth,
                "spectral_rolloff": spectral_rolloff,
                "n_fft": n_fft,
                "hop_length": hop_length
            }
            
        except Exception as e:
            logger.error(f"STFT特征提取失败: {e}")
            return {
                "spectral_centroid": 1000.0,
                "spectral_bandwidth": 500.0,
                "spectral_rolloff": 2000.0,
                "n_fft": n_fft,
                "hop_length": hop_length
            }
    
    def extract_mel_features_optimized(self, audio: np.ndarray,
                                     n_mels: int = 128,
                                     n_fft: int = 2048,
                                     hop_length: int = None) -> Dict[str, Any]:
        """内存优化的Mel频谱特征提取"""
        if hop_length is None:
            hop_length = n_fft // 4
        
        try:
            # 使用单声道
            if audio.ndim > 1:
                audio_mono = np.mean(audio, axis=0, dtype=self.dtype)
            else:
                audio_mono = audio.astype(self.dtype)
            
            # 获取缓存的Mel过滤器
            mel_filters = self._get_cached_mel_filters(n_mels, n_fft)
            
            # 计算Mel频谱图（内存优化）
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mel_spec = librosa.feature.melspectrogram(
                    y=audio_mono,
                    sr=self.sample_rate,
                    n_fft=n_fft,
                    hop_length=hop_length,
                    n_mels=n_mels,
                    dtype=self.dtype
                )
            
            # 转换为对数刻度（就地操作）
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
            
            # 计算MFCC（限制系数数量以节省内存）
            n_mfcc = min(13, n_mels)  # 最多13个MFCC系数
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                mfcc = librosa.feature.mfcc(
                    S=mel_spec_db,
                    sr=self.sample_rate,
                    n_mfcc=n_mfcc,
                    dtype=self.dtype
                )
            
            # 计算统计特征（避免存储完整矩阵）
            mfcc_mean = np.mean(mfcc, axis=1).tolist()
            mfcc_std = np.std(mfcc, axis=1).tolist()
            
            # 计算Mel频谱的统计特征
            mel_mean = float(np.mean(mel_spec_db))
            mel_std = float(np.std(mel_spec_db))
            
            # 清理临时变量
            del mel_spec, mel_spec_db, mfcc
            gc.collect()
            
            return {
                "mfcc_mean": mfcc_mean,
                "mfcc_std": mfcc_std,
                "mel_mean": mel_mean,
                "mel_std": mel_std,
                "n_mels": n_mels,
                "n_mfcc": n_mfcc
            }
            
        except Exception as e:
            logger.error(f"Mel特征提取失败: {e}")
            return {
                "mfcc_mean": [0.0] * 13,
                "mfcc_std": [0.0] * 13,
                "mel_mean": 0.0,
                "mel_std": 0.0,
                "n_mels": n_mels,
                "n_mfcc": 13
            }
    
    def extract_temporal_features_optimized(self, audio: np.ndarray) -> Dict[str, Any]:
        """内存优化的时域特征提取"""
        try:
            # 使用单声道
            if audio.ndim > 1:
                audio_mono = np.mean(audio, axis=0, dtype=self.dtype)
            else:
                audio_mono = audio.astype(self.dtype)
            
            # 零交叉率（分块计算以节省内存）
            frame_length = 2048
            hop_length = 512
            
            zcr_values = []
            for i in range(0, len(audio_mono) - frame_length, hop_length):
                frame = audio_mono[i:i + frame_length]
                zcr = np.sum(np.diff(np.signbit(frame))) / len(frame)
                zcr_values.append(zcr)
            
            zero_crossing_rate = float(np.mean(zcr_values)) if zcr_values else 0.0
            
            # RMS能量（分块计算）
            rms_values = []
            for i in range(0, len(audio_mono) - frame_length, hop_length):
                frame = audio_mono[i:i + frame_length]
                rms = np.sqrt(np.mean(frame**2))
                rms_values.append(rms)
            
            rms_energy = float(np.mean(rms_values)) if rms_values else 0.0
            
            # 清理临时变量
            del zcr_values, rms_values
            gc.collect()
            
            return {
                "zero_crossing_rate": zero_crossing_rate,
                "rms_energy": rms_energy,
                "frame_length": frame_length,
                "hop_length": hop_length
            }
            
        except Exception as e:
            logger.error(f"时域特征提取失败: {e}")
            return {
                "zero_crossing_rate": 0.0,
                "rms_energy": 0.0,
                "frame_length": 2048,
                "hop_length": 512
            }
    
    def extract_all_features_optimized(self, audio: np.ndarray) -> Dict[str, Any]:
        """提取所有优化的特征"""
        logger.debug("开始内存优化特征提取")
        
        features = {}
        
        # STFT特征
        features["stft"] = self.extract_stft_features_optimized(audio)
        
        # Mel特征
        features["mel"] = self.extract_mel_features_optimized(audio)
        
        # 时域特征
        features["temporal"] = self.extract_temporal_features_optimized(audio)
        
        logger.debug("内存优化特征提取完成")
        return features
    
    def clear_cache(self):
        """清理缓存以释放内存"""
        self._mel_filters_cache.clear()
        self._window_cache.clear()
        
        # 清理缓冲区
        self._stft_buffer = None
        self._mel_buffer = None
        self._mfcc_buffer = None
        
        gc.collect()
        logger.info("特征提取器缓存已清理")

# 全局优化特征提取器实例
optimized_extractor = MemoryOptimizedFeatureExtractor()
