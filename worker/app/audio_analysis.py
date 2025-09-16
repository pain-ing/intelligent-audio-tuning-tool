"""
音频分析模块 - 实现真实的音频特征提取（内存优化版本）
"""

import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln
from typing import Dict, Tuple, Optional, Iterator
import logging
from scipy import signal
from scipy.stats import pearsonr
import gc

# 导入流式处理模块
from .audio_streaming import MemoryAwareAudioLoader, AudioChunk, memory_efficient_audio_processing

# 导入优化的特征提取器
from .audio_features_optimized import MemoryOptimizedFeatureExtractor

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """音频分析器（内存优化版本）"""

    def __init__(self, sample_rate: int = 48000, max_memory_mb: float = 512.0):
        self.sample_rate = sample_rate
        self.meter = pyln.Meter(sample_rate)  # LUFS meter
        self.max_memory_mb = max_memory_mb

        # 缓存 Mel 过滤器组以减少重复计算
        self._mel_filters_cache = {}

        # 内存优化：使用 float32 减少内存占用
        self.dtype = np.float32

        # 流式加载器
        self.streaming_loader = MemoryAwareAudioLoader(max_memory_mb=max_memory_mb, dtype=self.dtype)

        # 优化的特征提取器
        self.optimized_extractor = MemoryOptimizedFeatureExtractor(sample_rate=sample_rate, dtype=self.dtype)
        
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """加载音频文件（兼容性方法，建议使用流式处理）"""
        try:
            # 检查文件大小，决定是否使用流式处理
            import os
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

            if file_size_mb > 50:  # 大于50MB使用流式处理
                logger.warning(f"大文件 ({file_size_mb:.1f}MB) 建议使用流式处理方法")
                return self._load_audio_streaming_fallback(file_path)

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

    def _load_audio_streaming_fallback(self, file_path: str) -> Tuple[np.ndarray, int]:
        """大文件的流式加载回退方案"""
        logger.info("使用流式加载处理大音频文件")

        chunks_iterator, audio_info = self.streaming_loader.load_audio_streaming(file_path)

        # 收集所有块
        chunks = []
        total_samples = 0

        for chunk in chunks_iterator:
            chunks.append(chunk.data)
            total_samples += chunk.data.shape[1]

        if not chunks:
            raise ValueError("无法加载音频数据")

        # 合并块
        channels = chunks[0].shape[0]
        audio = np.zeros((channels, total_samples), dtype=self.dtype)

        current_pos = 0
        for chunk_data in chunks:
            chunk_samples = chunk_data.shape[1]
            audio[:, current_pos:current_pos + chunk_samples] = chunk_data
            current_pos += chunk_samples

        # 清理内存
        del chunks
        gc.collect()

        return audio, self.sample_rate
    
    def analyze_stft(self, audio: np.ndarray) -> Dict:
        """STFT 分析（内存优化版本）"""
        try:
            # 使用优化的特征提取器
            optimized_features = self.optimized_extractor.extract_stft_features_optimized(audio, n_fft=2048)

            # 转换为兼容格式
            return {
                "spectral_centroid": optimized_features["spectral_centroid"],
                "spectral_bandwidth": optimized_features["spectral_bandwidth"],
                "spectral_rolloff": optimized_features["spectral_rolloff"],
                "primary_window": optimized_features["n_fft"],
                "hop_length": optimized_features["hop_length"]
            }
        except Exception as e:
            logger.error(f"优化STFT分析失败，回退到传统方法: {e}")
            return self._analyze_stft_fallback(audio)

    def _analyze_stft_fallback(self, audio: np.ndarray) -> Dict:
        """STFT分析回退方法"""
        try:
            # 使用单声道进行分析
            if audio.ndim > 1:
                audio_mono = audio[0].astype(self.dtype)
            else:
                audio_mono = audio.astype(self.dtype)

            n_fft = 2048
            hop_length = n_fft // 4

            # 计算基本的频谱特征
            spectral_centroid = librosa.feature.spectral_centroid(
                y=audio_mono, sr=self.sample_rate, hop_length=hop_length)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(
                y=audio_mono, sr=self.sample_rate, hop_length=hop_length)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio_mono, sr=self.sample_rate, hop_length=hop_length)[0]

            return {
                "spectral_centroid": float(np.mean(spectral_centroid)),
                "spectral_bandwidth": float(np.mean(spectral_bandwidth)),
                "spectral_rolloff": float(np.mean(spectral_rolloff)),
                "primary_window": n_fft,
                "hop_length": hop_length
            }

        except Exception as e:
            logger.error(f"STFT回退分析也失败: {e}")
            return {
                "spectral_centroid": 1000.0,
                "spectral_bandwidth": 500.0,
                "spectral_rolloff": 2000.0,
                "primary_window": 2048,
                "hop_length": 512
            }
    
    def analyze_mel_spectrum(self, audio: np.ndarray) -> Dict:
        """Mel 频谱分析（内存优化版本）"""
        try:
            # 使用优化的特征提取器
            optimized_features = self.optimized_extractor.extract_mel_features_optimized(audio, n_mels=128)

            # 转换为兼容格式
            return {
                "n_mels": optimized_features["n_mels"],
                "mfcc_mean": optimized_features["mfcc_mean"],
                "mfcc_std": optimized_features["mfcc_std"],
                "mel_mean": optimized_features["mel_mean"],
                "mel_std": optimized_features["mel_std"]
            }
        except Exception as e:
            logger.error(f"优化Mel分析失败，回退到传统方法: {e}")
            return self._analyze_mel_fallback(audio)

    def _analyze_mel_fallback(self, audio: np.ndarray) -> Dict:
        """Mel分析回退方法"""
        try:
            n_mels = 128

            # 使用单声道
            if audio.ndim > 1:
                audio_mono = audio[0].astype(self.dtype)
            else:
                audio_mono = audio.astype(self.dtype)

            # 计算 Mel 频谱
            mel_spec = librosa.feature.melspectrogram(
                y=audio_mono,
                sr=self.sample_rate,
                n_mels=n_mels,
                fmax=self.sample_rate//2,
                dtype=self.dtype
            )
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

            # 计算MFCC
            mfcc = librosa.feature.mfcc(S=mel_spec_db, sr=self.sample_rate, n_mfcc=13)

            # 清理临时变量
            del mel_spec
            gc.collect()

            return {
                "n_mels": n_mels,
                "mfcc_mean": np.mean(mfcc, axis=1).tolist(),
                "mfcc_std": np.std(mfcc, axis=1).tolist(),
                "mel_mean": float(np.mean(mel_spec_db)),
                "mel_std": float(np.std(mel_spec_db))
            }

        except Exception as e:
            logger.error(f"Mel回退分析也失败: {e}")
            return {
                "n_mels": 128,
                "mfcc_mean": [0.0] * 13,
                "mfcc_std": [0.0] * 13,
                "mel_mean": 0.0,
                "mel_std": 0.0
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
    
    def analyze_features(self, file_path: str, use_streaming: bool = None) -> Dict:
        """完整的音频特征分析（带缓存和流式处理）"""
        logger.info(f"Starting audio analysis for: {file_path}")

        # 尝试缓存
        try:
            from app.cache import cache_get, cache_set, make_file_hash
            file_hash = make_file_hash(file_path)
            cache_key = f"v2:{self.sample_rate}:{file_hash}"  # v2表示支持流式处理
            cached = cache_get("features", cache_key)
            if cached:
                logger.info("Analysis cache hit")
                return cached
        except Exception:
            cached = None

        # 决定是否使用流式处理
        if use_streaming is None:
            import os
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            use_streaming = file_size_mb > 20  # 大于20MB使用流式处理

        if use_streaming:
            logger.info("使用流式处理进行特征分析")
            features = self._analyze_features_streaming(file_path)
        else:
            # 传统方式：加载整个音频
            audio, sr = self.load_audio(file_path)
            features = self._analyze_features_traditional(audio, sr)

        # 写入缓存
        try:
            cache_set("features", cache_key, features, ttl_sec=24 * 3600)
        except Exception:
            pass

        logger.info("Audio analysis completed")
        return features

    def _analyze_features_traditional(self, audio: np.ndarray, sr: int) -> Dict:
        """传统的特征分析方法"""
        return {
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

    def _analyze_features_streaming(self, file_path: str) -> Dict:
        """流式特征分析方法"""
        chunks_iterator, audio_info = self.streaming_loader.load_audio_streaming(file_path)

        # 初始化累积器
        stft_accumulator = []
        mel_accumulator = []
        lufs_accumulator = []
        peak_accumulator = []
        f0_accumulator = []
        stereo_accumulator = []
        reverb_accumulator = []

        total_samples = 0
        chunk_count = 0

        try:
            for chunk in chunks_iterator:
                chunk_count += 1
                total_samples += chunk.data.shape[1]

                logger.debug(f"分析音频块 {chunk_count}")

                # 分析每个块
                stft_features = self.analyze_stft(chunk.data)
                mel_features = self.analyze_mel_spectrum(chunk.data)
                lufs_features = self.analyze_loudness(chunk.data)
                peak_features = self.analyze_true_peak(chunk.data)
                f0_features = self.analyze_f0(chunk.data)
                stereo_features = self.analyze_stereo(chunk.data)
                reverb_features = self.analyze_reverb(chunk.data)

                # 累积结果
                stft_accumulator.append(stft_features)
                mel_accumulator.append(mel_features)
                lufs_accumulator.append(lufs_features)
                peak_accumulator.append(peak_features)
                f0_accumulator.append(f0_features)
                stereo_accumulator.append(stereo_features)
                reverb_accumulator.append(reverb_features)

                # 定期清理内存
                if chunk_count % 10 == 0:
                    gc.collect()

            # 合并所有块的分析结果
            merged_features = self._merge_streaming_features(
                stft_accumulator, mel_accumulator, lufs_accumulator,
                peak_accumulator, f0_accumulator, stereo_accumulator,
                reverb_accumulator
            )

            # 添加音频信息
            merged_features["audio_info"] = {
                "sample_rate": self.sample_rate,
                "channels": audio_info["channels"],
                "duration_seconds": audio_info["duration"],
                "samples": total_samples
            }

            logger.info(f"流式分析完成: 处理了 {chunk_count} 个块")
            return merged_features

        except Exception as e:
            logger.error(f"流式特征分析失败: {e}")
            raise
        finally:
            # 清理内存
            del stft_accumulator, mel_accumulator, lufs_accumulator
            del peak_accumulator, f0_accumulator, stereo_accumulator, reverb_accumulator
            gc.collect()

    def _merge_streaming_features(self, stft_acc, mel_acc, lufs_acc,
                                 peak_acc, f0_acc, stereo_acc, reverb_acc) -> Dict:
        """合并流式处理的特征分析结果"""
        try:
            # 合并STFT特征
            stft_merged = self._merge_stft_features(stft_acc)

            # 合并Mel特征
            mel_merged = self._merge_mel_features(mel_acc)

            # 合并LUFS特征
            lufs_merged = self._merge_lufs_features(lufs_acc)

            # 合并峰值特征
            peak_merged = self._merge_peak_features(peak_acc)

            # 合并F0特征
            f0_merged = self._merge_f0_features(f0_acc)

            # 合并立体声特征
            stereo_merged = self._merge_stereo_features(stereo_acc)

            # 合并混响特征
            reverb_merged = self._merge_reverb_features(reverb_acc)

            return {
                "stft": stft_merged,
                "mel": mel_merged,
                "lufs": lufs_merged,
                "true_peak_db": peak_merged,
                "f0": f0_merged,
                "stereo": stereo_merged,
                "reverb": reverb_merged
            }

        except Exception as e:
            logger.error(f"合并流式特征失败: {e}")
            raise

    def _merge_stft_features(self, stft_acc) -> Dict:
        """合并STFT特征"""
        if not stft_acc:
            return {}

        # 计算平均值
        centroid_values = [f.get("spectral_centroid", 0) for f in stft_acc if f.get("spectral_centroid")]
        bandwidth_values = [f.get("spectral_bandwidth", 0) for f in stft_acc if f.get("spectral_bandwidth")]
        rolloff_values = [f.get("spectral_rolloff", 0) for f in stft_acc if f.get("spectral_rolloff")]

        return {
            "spectral_centroid": float(np.mean(centroid_values)) if centroid_values else 0.0,
            "spectral_bandwidth": float(np.mean(bandwidth_values)) if bandwidth_values else 0.0,
            "spectral_rolloff": float(np.mean(rolloff_values)) if rolloff_values else 0.0,
            "chunks_analyzed": len(stft_acc)
        }

    def _merge_mel_features(self, mel_acc) -> Dict:
        """合并Mel特征"""
        if not mel_acc:
            return {}

        # 收集所有MFCC值
        mfcc_values = []
        for f in mel_acc:
            if f.get("mfcc_mean"):
                mfcc_values.append(f["mfcc_mean"])

        if mfcc_values:
            # 计算平均MFCC
            mfcc_mean = np.mean(mfcc_values, axis=0).tolist()
        else:
            mfcc_mean = [0.0] * 13

        return {
            "mfcc_mean": mfcc_mean,
            "chunks_analyzed": len(mel_acc)
        }

    def _merge_lufs_features(self, lufs_acc) -> Dict:
        """合并LUFS特征"""
        if not lufs_acc:
            return {"integrated_lufs": -23.0, "short_term_lufs": [], "lufs_range": 0.0}

        # 收集所有LUFS值
        integrated_values = [f.get("integrated_lufs", -23.0) for f in lufs_acc]
        short_term_values = []

        for f in lufs_acc:
            short_term_values.extend(f.get("short_term_lufs", []))

        # 计算整体LUFS（加权平均）
        valid_integrated = [v for v in integrated_values if not np.isnan(v) and not np.isinf(v)]
        integrated_lufs = float(np.mean(valid_integrated)) if valid_integrated else -23.0

        # 限制短期LUFS数量
        short_term_lufs = short_term_values[:20]  # 最多保存20个值
        lufs_range = float(max(short_term_lufs) - min(short_term_lufs)) if short_term_lufs else 0.0

        return {
            "integrated_lufs": integrated_lufs,
            "short_term_lufs": short_term_lufs,
            "lufs_range": lufs_range
        }

    def _merge_peak_features(self, peak_acc) -> float:
        """合并峰值特征"""
        if not peak_acc:
            return -6.0

        # 取最大峰值
        peak_values = [p for p in peak_acc if not np.isnan(p) and not np.isinf(p)]
        return float(max(peak_values)) if peak_values else -6.0

    def _merge_f0_features(self, f0_acc) -> Dict:
        """合并F0特征"""
        if not f0_acc:
            return {"algorithm": "yin", "mean_f0": 0.0, "std_f0": 0.0,
                   "f0_range": 0.0, "voiced_ratio": 0.0, "sample_values": []}

        # 收集所有F0值
        mean_f0_values = [f.get("mean_f0", 0) for f in f0_acc if f.get("mean_f0", 0) > 0]
        voiced_ratios = [f.get("voiced_ratio", 0) for f in f0_acc]

        if mean_f0_values:
            mean_f0 = float(np.mean(mean_f0_values))
            std_f0 = float(np.std(mean_f0_values))
            f0_range = float(max(mean_f0_values) - min(mean_f0_values))
        else:
            mean_f0 = std_f0 = f0_range = 0.0

        voiced_ratio = float(np.mean(voiced_ratios)) if voiced_ratios else 0.0

        return {
            "algorithm": "yin",
            "mean_f0": mean_f0,
            "std_f0": std_f0,
            "f0_range": f0_range,
            "voiced_ratio": voiced_ratio,
            "sample_values": mean_f0_values[:10]  # 采样10个值
        }

    def _merge_stereo_features(self, stereo_acc) -> Dict:
        """合并立体声特征"""
        if not stereo_acc:
            return {"width": 1.0, "correlation": 1.0, "balance": 0.0}

        width_values = [f.get("width", 1.0) for f in stereo_acc]
        correlation_values = [f.get("correlation", 1.0) for f in stereo_acc]
        balance_values = [f.get("balance", 0.0) for f in stereo_acc]

        return {
            "width": float(np.mean(width_values)),
            "correlation": float(np.mean(correlation_values)),
            "balance": float(np.mean(balance_values))
        }

    def _merge_reverb_features(self, reverb_acc) -> Dict:
        """合并混响特征"""
        if not reverb_acc:
            return {"rt60_estimate": 0.5, "energy_decay_rate": 0.0, "reverb_presence": 0.0}

        rt60_values = [f.get("rt60_estimate", 0.5) for f in reverb_acc]
        decay_values = [f.get("energy_decay_rate", 0.0) for f in reverb_acc]
        presence_values = [f.get("reverb_presence", 0.0) for f in reverb_acc]

        return {
            "rt60_estimate": float(np.mean(rt60_values)),
            "energy_decay_rate": float(np.mean(decay_values)),
            "reverb_presence": float(np.mean(presence_values))
        }

# 全局分析器实例（内存优化版本）
analyzer = AudioAnalyzer(max_memory_mb=512.0)
