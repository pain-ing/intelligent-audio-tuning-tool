"""
参数反演模块 - 从参考和目标音频特征中估计风格参数
"""

import numpy as np
from typing import Dict, Literal, List, Tuple
import logging
from scipy import signal
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)

class ParameterInverter:
    """参数反演器"""
    
    def __init__(self):
        self.eq_bands = [
            {"freq": 60, "type": "highpass"},
            {"freq": 200, "type": "peaking"},
            {"freq": 500, "type": "peaking"},
            {"freq": 1000, "type": "peaking"},
            {"freq": 2000, "type": "peaking"},
            {"freq": 4000, "type": "peaking"},
            {"freq": 8000, "type": "peaking"},
            {"freq": 16000, "type": "lowpass"}
        ]
    
    def invert_eq_parameters(self, ref_features: Dict, tgt_features: Dict) -> List[Dict]:
        """反演均衡器参数"""
        eq_params = []
        
        # 从 STFT 特征中提取频谱信息
        ref_stft = ref_features.get("stft", {}).get("features", {}).get("win_2048", {})
        tgt_stft = tgt_features.get("stft", {}).get("features", {}).get("win_2048", {})
        
        # 基于频谱质心和带宽差异估计 EQ
        ref_centroid = ref_stft.get("spectral_centroid", 1000)
        tgt_centroid = tgt_stft.get("spectral_centroid", 1000)
        ref_bandwidth = ref_stft.get("spectral_bandwidth", 1000)
        tgt_bandwidth = tgt_stft.get("spectral_bandwidth", 1000)
        
        # 计算频谱差异
        centroid_ratio = ref_centroid / (tgt_centroid + 1e-6)
        bandwidth_ratio = ref_bandwidth / (tgt_bandwidth + 1e-6)
        
        # 生成 EQ 参数
        for i, band in enumerate(self.eq_bands):
            if band["type"] == "peaking":
                # 基于频谱差异计算增益
                freq_factor = band["freq"] / 1000.0  # 归一化频率
                
                if centroid_ratio > 1.1:  # 参考音频更亮
                    if freq_factor > 1.0:  # 高频
                        gain = min(6.0, (centroid_ratio - 1) * 12)
                    else:  # 低频
                        gain = max(-3.0, -(centroid_ratio - 1) * 6)
                elif centroid_ratio < 0.9:  # 参考音频更暗
                    if freq_factor > 1.0:  # 高频
                        gain = max(-6.0, -(1 - centroid_ratio) * 12)
                    else:  # 低频
                        gain = min(3.0, (1 - centroid_ratio) * 6)
                else:
                    gain = 0.0
                
                # 添加一些随机性以避免过度拟合
                gain += np.random.normal(0, 0.5)
                gain = np.clip(gain, -12.0, 12.0)
                
                if abs(gain) > 0.5:  # 只添加有意义的 EQ
                    eq_params.append({
                        "type": "peaking",
                        "f_hz": band["freq"],
                        "q": 1.0 + np.random.uniform(-0.3, 0.3),
                        "gain_db": float(gain)
                    })
        
        return eq_params[:6]  # 最多6段EQ
    
    def invert_lufs_parameters(self, ref_features: Dict, tgt_features: Dict) -> Dict:
        """反演响度参数"""
        ref_lufs = ref_features.get("lufs", {}).get("integrated_lufs", -23.0)
        tgt_lufs = tgt_features.get("lufs", {}).get("integrated_lufs", -23.0)
        
        # 目标响度设置为参考响度
        target_lufs = ref_lufs
        
        # 确保在合理范围内
        target_lufs = np.clip(target_lufs, -30.0, -6.0)
        
        return {"target_lufs": float(target_lufs)}
    
    def invert_limiter_parameters(self, ref_features: Dict, tgt_features: Dict) -> Dict:
        """反演限制器参数"""
        ref_tp = ref_features.get("true_peak_db", -1.0)
        tgt_tp = tgt_features.get("true_peak_db", -1.0)
        
        # 设置真峰值目标
        target_tp = min(ref_tp, -0.1)  # 至少留0.1dB余量
        target_tp = np.clip(target_tp, -3.0, -0.1)
        
        # 根据峰值差异调整参数
        tp_diff = abs(ref_tp - tgt_tp)
        if tp_diff > 3.0:
            lookahead_ms = 5.0  # 更激进的限制
            release_ms = 50.0
        else:
            lookahead_ms = 1.0  # 温和的限制
            release_ms = 100.0
        
        return {
            "tp_db": float(target_tp),
            "lookahead_ms": lookahead_ms,
            "release_ms": release_ms
        }
    
    def invert_reverb_parameters(self, ref_features: Dict, tgt_features: Dict) -> Dict:
        """反演混响参数"""
        ref_reverb = ref_features.get("reverb", {})
        tgt_reverb = tgt_features.get("reverb", {})
        
        ref_rt60 = ref_reverb.get("rt60_estimate", 0.5)
        tgt_rt60 = tgt_reverb.get("rt60_estimate", 0.5)
        ref_presence = ref_reverb.get("reverb_presence", 0.0)
        
        # 计算混响差异
        rt60_diff = ref_rt60 - tgt_rt60
        
        if ref_presence > 0.5 and rt60_diff > 0.2:
            # 需要添加混响
            mix_level = min(0.3, rt60_diff * 0.5)
            ir_type = "hall" if ref_rt60 > 1.5 else "room"
        else:
            # 不需要或轻微混响
            mix_level = max(0.0, rt60_diff * 0.2)
            ir_type = "room"
        
        return {
            "ir_key": f"ir/{ir_type}_default.wav",
            "mix": float(np.clip(mix_level, 0.0, 0.5)),
            "pre_delay_ms": 20.0 if ir_type == "hall" else 10.0
        }
    
    def invert_stereo_parameters(self, ref_features: Dict, tgt_features: Dict) -> Dict:
        """反演立体声参数"""
        ref_stereo = ref_features.get("stereo", {})
        tgt_stereo = tgt_features.get("stereo", {})
        
        ref_width = ref_stereo.get("width", 1.0)
        tgt_width = tgt_stereo.get("width", 1.0)
        ref_correlation = ref_stereo.get("correlation", 1.0)
        
        # 计算目标宽度
        if ref_stereo.get("is_stereo", False) and tgt_stereo.get("is_stereo", False):
            width_ratio = ref_width / (tgt_width + 1e-6)
            target_width = np.clip(width_ratio, 0.5, 2.0)
        else:
            target_width = 1.0
        
        return {"width": float(target_width)}
    
    def invert_pitch_parameters(self, ref_features: Dict, tgt_features: Dict, mode: Literal["A", "B"]) -> Dict:
        """反演音高参数"""
        ref_f0 = ref_features.get("f0", {})
        tgt_f0 = tgt_features.get("f0", {})
        
        ref_mean_f0 = ref_f0.get("mean_f0", 0)
        tgt_mean_f0 = tgt_f0.get("mean_f0", 0)
        
        if mode == "A" and ref_mean_f0 > 0 and tgt_mean_f0 > 0:
            # A模式：同源音频，可以进行音高校正
            f0_ratio = ref_mean_f0 / tgt_mean_f0
            semitones = 12 * np.log2(f0_ratio)
            semitones = np.clip(semitones, -12, 12)  # 限制在一个八度内
            
            if abs(semitones) > 0.1:  # 只有显著差异才调整
                return {"semitones": float(semitones)}
        
        return {"semitones": 0.0}
    
    def estimate_compression_parameters(self, ref_features: Dict, tgt_features: Dict) -> Dict:
        """估计压缩参数 (简化版)"""
        ref_lufs = ref_features.get("lufs", {})
        tgt_lufs = tgt_features.get("lufs", {})
        
        ref_range = ref_lufs.get("lufs_range", 0)
        tgt_range = tgt_lufs.get("lufs_range", 0)
        
        # 基于动态范围差异估计压缩
        if ref_range < tgt_range * 0.7:  # 参考音频动态范围更小
            ratio = min(4.0, tgt_range / (ref_range + 1e-6))
            threshold = -20.0
            attack_ms = 10.0
            release_ms = 100.0
            
            return {
                "enabled": True,
                "threshold_db": threshold,
                "ratio": float(ratio),
                "attack_ms": attack_ms,
                "release_ms": release_ms
            }
        
        return {"enabled": False}
    
    def invert_parameters(self, ref_features: Dict, tgt_features: Dict, mode: Literal["A", "B"]) -> Dict:
        """主要的参数反演函数"""
        logger.info(f"Starting parameter inversion (mode: {mode})")
        
        # 反演各个模块的参数
        eq_params = self.invert_eq_parameters(ref_features, tgt_features)
        lufs_params = self.invert_lufs_parameters(ref_features, tgt_features)
        limiter_params = self.invert_limiter_parameters(ref_features, tgt_features)
        reverb_params = self.invert_reverb_parameters(ref_features, tgt_features)
        stereo_params = self.invert_stereo_parameters(ref_features, tgt_features)
        pitch_params = self.invert_pitch_parameters(ref_features, tgt_features, mode)
        compression_params = self.estimate_compression_parameters(ref_features, tgt_features)
        
        # 组合所有参数
        style_params = {
            "eq": eq_params,
            "lufs": lufs_params,
            "limiter": limiter_params,
            "reverb": reverb_params,
            "stereo": stereo_params,
            "pitch": pitch_params,
            "compression": compression_params,
            "metadata": {
                "mode": mode,
                "confidence": self.calculate_confidence(ref_features, tgt_features),
                "processing_chain": ["eq", "compression", "reverb", "stereo", "pitch", "lufs", "limiter"]
            }
        }
        
        logger.info("Parameter inversion completed")
        return style_params
    
    def calculate_confidence(self, ref_features: Dict, tgt_features: Dict) -> float:
        """计算参数反演的置信度"""
        confidence_factors = []
        
        # 基于音频长度的置信度
        ref_duration = ref_features.get("audio_info", {}).get("duration_seconds", 0)
        tgt_duration = tgt_features.get("audio_info", {}).get("duration_seconds", 0)
        
        if ref_duration > 10 and tgt_duration > 10:
            confidence_factors.append(0.9)
        elif ref_duration > 5 and tgt_duration > 5:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        # 基于频谱特征的置信度
        ref_stft = ref_features.get("stft", {}).get("features", {}).get("win_2048", {})
        tgt_stft = tgt_features.get("stft", {}).get("features", {}).get("win_2048", {})
        
        if ref_stft and tgt_stft:
            # 检查频谱特征的相似性
            centroid_diff = abs(ref_stft.get("spectral_centroid", 1000) - 
                              tgt_stft.get("spectral_centroid", 1000))
            if centroid_diff < 500:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.6)
        
        return float(np.mean(confidence_factors)) if confidence_factors else 0.5
