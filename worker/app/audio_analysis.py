"""
音频分析模块 - 实现真实的音频特征提取
"""

import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln
from typing import Dict, Tuple, Optional
import logging
from scipy import signal
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """音频分析器"""
    
    def __init__(self, sample_rate: int = 48000):
        self.sample_rate = sample_rate
        self.meter = pyln.Meter(sample_rate)  # LUFS meter

        # 缓存 Mel 过滤器组以减少重复计算
        self._mel_filters_cache = {}

        # 内存优化：使用 float32 减少内存占用
        self.dtype = np.float32
        
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """加载音频文件"""
        try:
            # 使用 librosa 加载音频，指定 dtype 为 float32 节省内存
            audio, sr = librosa.load(file_path, sr=self.sample_rate, mono=False, dtype=self.dtype)

            # 确保是 2D 数组 (channels, samples)
            if audio.ndim == 1:
                audio = audio.reshape(1, -1)
            elif audio.ndim == 2 and audio.shape[0] > audio.shape[1]:
                audio = audio.T  # 转置为 (channels, samples)

            # 确保数据类型为 float32
            audio = audio.astype(self.dtype)

            logger.info(f"Loaded audio: {audio.shape} at {sr}Hz, dtype: {audio.dtype}")
            return audio, sr
            
        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {e}")
            raise
    
    def analyze_stft(self, audio: np.ndarray) -> Dict:
        """STFT 分析"""
        # 使用多个窗口大小进行分析
        window_sizes = [1024, 2048, 4096]
        stft_features = {}
        
        for win_size in window_sizes:
            hop_length = win_size // 4
            
            # 计算 STFT
            stft = librosa.stft(audio[0], n_fft=win_size, hop_length=hop_length)
            magnitude = np.abs(stft)
            magnitude_db = librosa.amplitude_to_db(magnitude)
            
            # 统计特征
            stft_features[f"win_{win_size}"] = {
                "magnitude_mean": float(np.mean(magnitude_db)),
                "magnitude_std": float(np.std(magnitude_db)),
                "magnitude_max": float(np.max(magnitude_db)),
                "magnitude_min": float(np.min(magnitude_db)),
                "spectral_centroid": float(np.mean(librosa.feature.spectral_centroid(
                    y=audio[0], sr=self.sample_rate, hop_length=hop_length)[0])),
                "spectral_bandwidth": float(np.mean(librosa.feature.spectral_bandwidth(
                    y=audio[0], sr=self.sample_rate, hop_length=hop_length)[0])),
                "spectral_rolloff": float(np.mean(librosa.feature.spectral_rolloff(
                    y=audio[0], sr=self.sample_rate, hop_length=hop_length)[0]))
            }
        
        return {
            "features": stft_features,
            "primary_window": 2048,
            "hop_length": 512
        }
    
    def analyze_mel_spectrum(self, audio: np.ndarray) -> Dict:
        """Mel 频谱分析（内存优化版）"""
        n_mels = 128

        # 使用缓存的 Mel 过滤器组
        cache_key = (n_mels, self.sample_rate)
        if cache_key not in self._mel_filters_cache:
            self._mel_filters_cache[cache_key] = librosa.filters.mel(
                sr=self.sample_rate,
                n_fft=2048,
                n_mels=n_mels,
                fmax=self.sample_rate//2
            ).astype(self.dtype)

        # 计算 Mel 频谱，使用 float32
        mel_spec = librosa.feature.melspectrogram(
            y=audio[0].astype(self.dtype),
            sr=self.sample_rate,
            n_mels=n_mels,
            fmax=self.sample_rate//2,
            dtype=self.dtype
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        
        # 统计特征
        return {
            "n_mels": n_mels,
            "mean": float(np.mean(mel_spec_db)),
            "std": float(np.std(mel_spec_db)),
            "energy_distribution": [float(x) for x in np.mean(mel_spec_db, axis=1)[:20]],  # 前20个Mel频带
            "temporal_variance": float(np.mean(np.var(mel_spec_db, axis=1)))
        }
    
    def analyze_loudness(self, audio: np.ndarray) -> Dict:
        """响度分析 (EBU R128)"""
        # 转换为正确的形状用于 pyloudnorm
        if audio.shape[0] == 1:
            audio_mono = audio[0]
        else:
            audio_mono = np.mean(audio, axis=0)  # 混合为单声道
            
        # 计算 LUFS
        try:
            integrated_lufs = self.meter.integrated_loudness(audio_mono)
            
            # 计算短期响度 (每3秒)
            block_size = int(3.0 * self.sample_rate)
            short_term_lufs = []
            
            for i in range(0, len(audio_mono) - block_size, block_size):
                block = audio_mono[i:i + block_size]
                if len(block) >= block_size:
                    st_lufs = pyln.Meter(self.sample_rate).integrated_loudness(block)
                    if not np.isnan(st_lufs) and not np.isinf(st_lufs):
                        short_term_lufs.append(float(st_lufs))
            
            return {
                "integrated_lufs": float(integrated_lufs) if not np.isnan(integrated_lufs) else -23.0,
                "short_term_lufs": short_term_lufs[:10],  # 最多保存10个值
                "lufs_range": float(max(short_term_lufs) - min(short_term_lufs)) if short_term_lufs else 0.0
            }
            
        except Exception as e:
            logger.warning(f"LUFS calculation failed: {e}")
            return {
                "integrated_lufs": -23.0,  # 默认值
                "short_term_lufs": [],
                "lufs_range": 0.0
            }
    
    def analyze_true_peak(self, audio: np.ndarray) -> float:
        """真峰值分析"""
        # 上采样检测真峰值
        upsampled = signal.resample(audio.flatten(), len(audio.flatten()) * 4)
        true_peak = np.max(np.abs(upsampled))
        true_peak_db = 20 * np.log10(true_peak) if true_peak > 0 else -60.0
        
        return float(true_peak_db)
    
    def analyze_f0(self, audio: np.ndarray) -> Dict:
        """基频分析"""
        try:
            # 使用 librosa 的 YIN 算法
            f0 = librosa.yin(
                audio[0], 
                fmin=librosa.note_to_hz('C2'),  # ~65 Hz
                fmax=librosa.note_to_hz('C7'),  # ~2093 Hz
                sr=self.sample_rate
            )
            
            # 过滤无效值
            valid_f0 = f0[f0 > 0]
            
            if len(valid_f0) > 0:
                return {
                    "algorithm": "yin",
                    "mean_f0": float(np.mean(valid_f0)),
                    "std_f0": float(np.std(valid_f0)),
                    "f0_range": float(np.max(valid_f0) - np.min(valid_f0)),
                    "voiced_ratio": float(len(valid_f0) / len(f0)),
                    "sample_values": [float(x) for x in valid_f0[::len(valid_f0)//10]][:10]  # 采样10个值
                }
            else:
                return {
                    "algorithm": "yin",
                    "mean_f0": 0.0,
                    "std_f0": 0.0,
                    "f0_range": 0.0,
                    "voiced_ratio": 0.0,
                    "sample_values": []
                }
                
        except Exception as e:
            logger.warning(f"F0 analysis failed: {e}")
            return {
                "algorithm": "yin",
                "mean_f0": 0.0,
                "std_f0": 0.0,
                "f0_range": 0.0,
                "voiced_ratio": 0.0,
                "sample_values": []
            }
    
    def analyze_stereo(self, audio: np.ndarray) -> Dict:
        """立体声分析"""
        if audio.shape[0] < 2:
            # 单声道，返回默认值
            return {
                "is_stereo": False,
                "correlation": 1.0,
                "width": 0.0,
                "mid_energy": 1.0,
                "side_energy": 0.0
            }
        
        left = audio[0]
        right = audio[1]
        
        # M/S 编码
        mid = (left + right) / 2
        side = (left - right) / 2
        
        # 计算能量
        mid_energy = float(np.mean(mid ** 2))
        side_energy = float(np.mean(side ** 2))
        
        # 计算相关性
        correlation, _ = pearsonr(left, right)
        correlation = float(correlation) if not np.isnan(correlation) else 1.0
        
        # 计算立体声宽度
        width = side_energy / (mid_energy + 1e-10)
        
        return {
            "is_stereo": True,
            "correlation": correlation,
            "width": float(width),
            "mid_energy": mid_energy,
            "side_energy": side_energy
        }
    
    def analyze_reverb(self, audio: np.ndarray) -> Dict:
        """混响分析 (简化版)"""
        try:
            # 计算能量衰减曲线 (EDC)
            audio_mono = audio[0] if audio.shape[0] == 1 else np.mean(audio, axis=0)
            
            # 计算瞬时能量
            frame_length = 2048
            hop_length = 512
            energy = []
            
            for i in range(0, len(audio_mono) - frame_length, hop_length):
                frame = audio_mono[i:i + frame_length]
                energy.append(np.sum(frame ** 2))
            
            energy = np.array(energy)
            
            # 简化的 RT60 估计
            if len(energy) > 10:
                # 找到能量峰值
                peak_idx = np.argmax(energy)
                if peak_idx < len(energy) - 5:
                    decay_energy = energy[peak_idx:]
                    
                    # 计算衰减时间 (简化)
                    decay_db = 10 * np.log10(decay_energy / (np.max(decay_energy) + 1e-10))
                    
                    # 寻找 -60dB 点
                    rt60_frames = 0
                    for i, db in enumerate(decay_db):
                        if db < -60:
                            rt60_frames = i
                            break
                    
                    rt60_seconds = rt60_frames * hop_length / self.sample_rate
                else:
                    rt60_seconds = 0.5  # 默认值
            else:
                rt60_seconds = 0.5
            
            return {
                "rt60_estimate": float(max(0.1, min(3.0, rt60_seconds))),  # 限制在合理范围
                "energy_decay_rate": float(np.mean(np.diff(energy[:10]))) if len(energy) > 10 else 0.0,
                "reverb_presence": float(rt60_seconds > 0.8)  # 简单的混响存在判断
            }
            
        except Exception as e:
            logger.warning(f"Reverb analysis failed: {e}")
            return {
                "rt60_estimate": 0.5,
                "energy_decay_rate": 0.0,
                "reverb_presence": 0.0
            }
    
    def analyze_features(self, file_path: str) -> Dict:
        """完整的音频特征分析（带缓存）"""
        logger.info(f"Starting audio analysis for: {file_path}")

        # 尝试缓存
        try:
            from app.cache import cache_get, cache_set, make_file_hash
            file_hash = make_file_hash(file_path)
            cache_key = f"v1:{self.sample_rate}:{file_hash}"
            cached = cache_get("features", cache_key)
            if cached:
                logger.info("Analysis cache hit")
                return cached
        except Exception:
            cached = None

        # 加载音频
        audio, sr = self.load_audio(file_path)

        # 执行各种分析
        features = {
            "stft": self.analyze_stft(audio),
            "mel": self.analyze_mel_spectrum(audio),
            "lufs": self.analyze_loudness(audio),
            "true_peak_db": self.analyze_true_peak(audio),
            "f0": self.analyze_f0(audio),
            "stereo": self.analyze_stereo(audio),
            "reverb": self.analyze_reverb(audio),
            "audio_info": {
                "sample_rate": sr,
                "channels": audio.shape[0],
                "duration_seconds": float(audio.shape[1] / sr),
                "samples": audio.shape[1]
            }
        }

        # 写入缓存
        try:
            cache_set("features", cache_key, features, ttl_sec=24 * 3600)
        except Exception:
            pass

        logger.info("Audio analysis completed")
        return features

# 全局分析器实例
analyzer = AudioAnalyzer()
