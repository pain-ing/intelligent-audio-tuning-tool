"""
音频格式转换器
"""

import os
import logging
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

import soundfile as sf
import librosa
import numpy as np

logger = logging.getLogger(__name__)


class AudioFormat(Enum):
    """支持的音频格式"""
    WAV = "wav"
    MP3 = "mp3"
    FLAC = "flac"
    AAC = "aac"
    OGG = "ogg"
    M4A = "m4a"
    WMA = "wma"
    AIFF = "aiff"
    AU = "au"


class AudioQuality(Enum):
    """音频质量设置"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    LOSSLESS = "lossless"


@dataclass
class AudioMetadata:
    """音频元数据"""
    duration: float
    sample_rate: int
    channels: int
    bit_depth: Optional[int] = None
    bitrate: Optional[int] = None
    format: Optional[str] = None
    file_size: int = 0
    
    @property
    def is_stereo(self) -> bool:
        return self.channels == 2
    
    @property
    def is_mono(self) -> bool:
        return self.channels == 1


@dataclass
class ConversionSettings:
    """转换设置"""
    target_format: AudioFormat
    target_sample_rate: Optional[int] = None
    target_channels: Optional[int] = None
    target_bit_depth: Optional[int] = None
    quality: AudioQuality = AudioQuality.HIGH
    normalize: bool = False
    trim_silence: bool = False
    fade_in: float = 0.0  # 淡入时间（秒）
    fade_out: float = 0.0  # 淡出时间（秒）
    
    # 压缩设置
    compression_level: Optional[int] = None  # FLAC压缩级别 (0-8)
    mp3_bitrate: int = 320  # MP3比特率 (kbps)
    aac_bitrate: int = 256  # AAC比特率 (kbps)


class AudioFormatConverter:
    """音频格式转换器"""
    
    def __init__(self):
        self.supported_input_formats = {
            ".wav", ".mp3", ".flac", ".aac", ".ogg", 
            ".m4a", ".wma", ".aiff", ".au"
        }
        
        self.supported_output_formats = {
            AudioFormat.WAV: [".wav"],
            AudioFormat.FLAC: [".flac"],
            AudioFormat.MP3: [".mp3"],
            AudioFormat.AAC: [".aac", ".m4a"],
            AudioFormat.OGG: [".ogg"],
            AudioFormat.AIFF: [".aiff", ".aif"],
            AudioFormat.AU: [".au"]
        }
        
        # 质量设置映射
        self.quality_settings = {
            AudioQuality.LOW: {"sample_rate": 22050, "bit_depth": 16},
            AudioQuality.MEDIUM: {"sample_rate": 44100, "bit_depth": 16},
            AudioQuality.HIGH: {"sample_rate": 48000, "bit_depth": 24},
            AudioQuality.LOSSLESS: {"sample_rate": 96000, "bit_depth": 32}
        }
        
        logger.info("音频格式转换器初始化完成")
    
    def get_audio_metadata(self, file_path: str) -> AudioMetadata:
        """获取音频文件元数据"""
        try:
            # 使用librosa获取基本信息
            y, sr = librosa.load(file_path, sr=None, mono=False)
            duration = librosa.get_duration(y=y, sr=sr)
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 尝试使用soundfile获取更详细信息
            try:
                with sf.SoundFile(file_path) as f:
                    channels = f.channels
                    sample_rate = f.samplerate
                    bit_depth = f.subtype_info.bits if hasattr(f.subtype_info, 'bits') else None
                    format_name = f.format
            except:
                # 回退到librosa信息
                channels = 1 if y.ndim == 1 else y.shape[0]
                sample_rate = sr
                bit_depth = None
                format_name = Path(file_path).suffix.lower()
            
            return AudioMetadata(
                duration=duration,
                sample_rate=sample_rate,
                channels=channels,
                bit_depth=bit_depth,
                format=format_name,
                file_size=file_size
            )
            
        except Exception as e:
            logger.error(f"获取音频元数据失败: {file_path}, 错误: {e}")
            raise
    
    def is_format_supported(self, file_path: str, for_input: bool = True) -> bool:
        """检查格式是否支持"""
        ext = Path(file_path).suffix.lower()
        
        if for_input:
            return ext in self.supported_input_formats
        else:
            # 检查输出格式
            return any(ext in exts for exts in self.supported_output_formats.values())
    
    def convert_audio(self, input_path: str, output_path: str, 
                     settings: ConversionSettings) -> Dict[str, Any]:
        """转换音频格式"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        if not self.is_format_supported(input_path, for_input=True):
            raise ValueError(f"不支持的输入格式: {input_path}")
        
        # 创建输出目录
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"开始音频格式转换: {input_path} -> {output_path}")
        
        try:
            # 获取输入文件元数据
            input_metadata = self.get_audio_metadata(input_path)
            
            # 加载音频数据
            audio_data, original_sr = librosa.load(
                input_path, 
                sr=None, 
                mono=False, 
                dtype=np.float32
            )
            
            # 应用转换设置
            processed_audio, target_sr = self._apply_conversion_settings(
                audio_data, original_sr, settings, input_metadata
            )

            # 保存转换后的音频
            self._save_converted_audio(
                processed_audio, output_path, settings, target_sr
            )
            
            # 获取输出文件元数据
            output_metadata = self.get_audio_metadata(output_path)
            
            # 返回转换结果
            result = {
                "success": True,
                "input_metadata": input_metadata,
                "output_metadata": output_metadata,
                "conversion_settings": settings,
                "size_reduction": (input_metadata.file_size - output_metadata.file_size) / input_metadata.file_size * 100
            }
            
            logger.info(f"音频格式转换完成: {input_path} -> {output_path}")
            return result
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {input_path} -> {output_path}, 错误: {e}")
            raise
    
    def _apply_conversion_settings(self, audio_data: np.ndarray, 
                                 original_sr: int, 
                                 settings: ConversionSettings,
                                 input_metadata: AudioMetadata) -> Tuple[np.ndarray, int]:
        """应用转换设置"""
        processed_audio = audio_data
        target_sr = original_sr
        
        # 重采样
        if settings.target_sample_rate and settings.target_sample_rate != original_sr:
            target_sr = settings.target_sample_rate
            processed_audio = librosa.resample(
                processed_audio, 
                orig_sr=original_sr, 
                target_sr=target_sr
            )
            logger.debug(f"重采样: {original_sr} Hz -> {target_sr} Hz")
        
        # 声道转换
        if settings.target_channels:
            if settings.target_channels == 1 and processed_audio.ndim > 1:
                # 转为单声道
                processed_audio = librosa.to_mono(processed_audio)
                logger.debug("转换为单声道")
            elif settings.target_channels == 2 and processed_audio.ndim == 1:
                # 转为立体声
                processed_audio = np.stack([processed_audio, processed_audio])
                logger.debug("转换为立体声")
        
        # 标准化
        if settings.normalize:
            max_val = np.max(np.abs(processed_audio))
            if max_val > 0:
                processed_audio = processed_audio / max_val * 0.95
            logger.debug("音频标准化完成")
        
        # 静音修剪
        if settings.trim_silence:
            processed_audio, _ = librosa.effects.trim(
                processed_audio, 
                top_db=20
            )
            logger.debug("静音修剪完成")
        
        # 淡入淡出
        if settings.fade_in > 0 or settings.fade_out > 0:
            processed_audio = self._apply_fade(
                processed_audio, target_sr, settings.fade_in, settings.fade_out
            )
            logger.debug(f"淡入淡出: {settings.fade_in}s / {settings.fade_out}s")
        
        return processed_audio, target_sr
    
    def _apply_fade(self, audio_data: np.ndarray, sample_rate: int, 
                   fade_in: float, fade_out: float) -> np.ndarray:
        """应用淡入淡出效果"""
        audio_length = audio_data.shape[-1]
        
        # 淡入
        if fade_in > 0:
            fade_in_samples = int(fade_in * sample_rate)
            fade_in_samples = min(fade_in_samples, audio_length // 4)
            
            fade_curve = np.linspace(0, 1, fade_in_samples)
            if audio_data.ndim == 1:
                audio_data[:fade_in_samples] *= fade_curve
            else:
                audio_data[:, :fade_in_samples] *= fade_curve
        
        # 淡出
        if fade_out > 0:
            fade_out_samples = int(fade_out * sample_rate)
            fade_out_samples = min(fade_out_samples, audio_length // 4)
            
            fade_curve = np.linspace(1, 0, fade_out_samples)
            if audio_data.ndim == 1:
                audio_data[-fade_out_samples:] *= fade_curve
            else:
                audio_data[:, -fade_out_samples:] *= fade_curve
        
        return audio_data
    
    def _save_converted_audio(self, audio_data: np.ndarray, output_path: str,
                            settings: ConversionSettings, sample_rate: int):
        """保存转换后的音频"""
        target_format = settings.target_format
        
        # 根据格式保存
        if target_format == AudioFormat.WAV:
            self._save_wav(audio_data, output_path, sample_rate, settings)
        elif target_format == AudioFormat.FLAC:
            self._save_flac(audio_data, output_path, sample_rate, settings)
        elif target_format in [AudioFormat.MP3, AudioFormat.AAC, AudioFormat.OGG]:
            self._save_compressed_format(audio_data, output_path, sample_rate, settings)
        else:
            # 使用soundfile保存其他格式
            sf.write(output_path, audio_data.T if audio_data.ndim > 1 else audio_data, sample_rate)
    
    def _save_wav(self, audio_data: np.ndarray, output_path: str, 
                 sample_rate: int, settings: ConversionSettings):
        """保存WAV格式"""
        # 确定位深度
        bit_depth = settings.target_bit_depth
        if not bit_depth:
            quality_settings = self.quality_settings[settings.quality]
            bit_depth = quality_settings["bit_depth"]
        
        # 确定子类型
        if bit_depth == 16:
            subtype = 'PCM_16'
        elif bit_depth == 24:
            subtype = 'PCM_24'
        elif bit_depth == 32:
            subtype = 'PCM_32'
        else:
            subtype = 'PCM_16'  # 默认
        
        sf.write(
            output_path, 
            audio_data.T if audio_data.ndim > 1 else audio_data, 
            sample_rate, 
            subtype=subtype
        )
    
    def _save_flac(self, audio_data: np.ndarray, output_path: str, 
                  sample_rate: int, settings: ConversionSettings):
        """保存FLAC格式"""
        # FLAC支持16位和24位
        bit_depth = settings.target_bit_depth or 24
        subtype = 'PCM_24' if bit_depth >= 24 else 'PCM_16'
        
        sf.write(
            output_path, 
            audio_data.T if audio_data.ndim > 1 else audio_data, 
            sample_rate, 
            subtype=subtype,
            format='FLAC'
        )
    
    def _save_compressed_format(self, audio_data: np.ndarray, output_path: str, 
                              sample_rate: int, settings: ConversionSettings):
        """保存压缩格式（MP3, AAC, OGG）"""
        # 先保存为临时WAV文件
        temp_wav = output_path + ".temp.wav"
        
        try:
            sf.write(temp_wav, audio_data.T if audio_data.ndim > 1 else audio_data, sample_rate)
            
            # 使用FFmpeg转换
            self._convert_with_ffmpeg(temp_wav, output_path, settings)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
    
    def _convert_with_ffmpeg(self, input_path: str, output_path: str, 
                           settings: ConversionSettings):
        """使用FFmpeg转换音频格式"""
        cmd = ["ffmpeg", "-i", input_path, "-y"]  # -y 覆盖输出文件
        
        target_format = settings.target_format
        
        if target_format == AudioFormat.MP3:
            cmd.extend(["-codec:a", "libmp3lame", "-b:a", f"{settings.mp3_bitrate}k"])
        elif target_format == AudioFormat.AAC:
            cmd.extend(["-codec:a", "aac", "-b:a", f"{settings.aac_bitrate}k"])
        elif target_format == AudioFormat.OGG:
            cmd.extend(["-codec:a", "libvorbis", "-q:a", "5"])
        
        # 添加采样率设置
        if settings.target_sample_rate:
            cmd.extend(["-ar", str(settings.target_sample_rate)])
        
        # 添加声道设置
        if settings.target_channels:
            cmd.extend(["-ac", str(settings.target_channels)])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            logger.debug(f"FFmpeg转换成功: {input_path} -> {output_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg转换失败: {e.stderr}")
            raise RuntimeError(f"FFmpeg转换失败: {e.stderr}")
        except FileNotFoundError:
            logger.error("FFmpeg未找到，请确保已安装FFmpeg")
            raise RuntimeError("FFmpeg未找到，请确保已安装FFmpeg")
    
    def batch_convert(self, file_pairs: List[Tuple[str, str]], 
                     settings: ConversionSettings) -> List[Dict[str, Any]]:
        """批量转换音频格式"""
        results = []
        
        for i, (input_path, output_path) in enumerate(file_pairs):
            try:
                logger.info(f"批量转换进度: {i+1}/{len(file_pairs)} - {input_path}")
                result = self.convert_audio(input_path, output_path, settings)
                results.append(result)
                
            except Exception as e:
                logger.error(f"批量转换失败: {input_path}, 错误: {e}")
                results.append({
                    "success": False,
                    "input_path": input_path,
                    "output_path": output_path,
                    "error": str(e)
                })
        
        return results
    
    def get_conversion_estimate(self, input_path: str, 
                              settings: ConversionSettings) -> Dict[str, Any]:
        """估算转换结果"""
        try:
            metadata = self.get_audio_metadata(input_path)
            
            # 估算输出文件大小
            estimated_size = self._estimate_output_size(metadata, settings)
            
            # 估算处理时间（基于文件大小和复杂度）
            estimated_time = self._estimate_processing_time(metadata, settings)
            
            return {
                "input_metadata": metadata,
                "estimated_output_size": estimated_size,
                "estimated_processing_time": estimated_time,
                "size_change_percent": (estimated_size - metadata.file_size) / metadata.file_size * 100
            }
            
        except Exception as e:
            logger.error(f"转换估算失败: {input_path}, 错误: {e}")
            raise
    
    def _estimate_output_size(self, metadata: AudioMetadata, 
                            settings: ConversionSettings) -> int:
        """估算输出文件大小"""
        # 基础计算：采样率 × 声道数 × 位深度 × 时长
        target_sr = settings.target_sample_rate or metadata.sample_rate
        target_channels = settings.target_channels or metadata.channels
        target_bit_depth = settings.target_bit_depth or 16
        
        if settings.target_format in [AudioFormat.WAV, AudioFormat.FLAC, AudioFormat.AIFF]:
            # 无损格式
            estimated_size = int(target_sr * target_channels * (target_bit_depth / 8) * metadata.duration)
            if settings.target_format == AudioFormat.FLAC:
                estimated_size = int(estimated_size * 0.6)  # FLAC压缩比约40%
        else:
            # 有损格式
            if settings.target_format == AudioFormat.MP3:
                estimated_size = int(settings.mp3_bitrate * 1000 * metadata.duration / 8)
            elif settings.target_format == AudioFormat.AAC:
                estimated_size = int(settings.aac_bitrate * 1000 * metadata.duration / 8)
            else:
                estimated_size = int(metadata.file_size * 0.3)  # 默认压缩比
        
        return estimated_size
    
    def _estimate_processing_time(self, metadata: AudioMetadata, 
                                settings: ConversionSettings) -> float:
        """估算处理时间"""
        # 基础时间：文件时长的倍数
        base_time = metadata.duration * 0.1  # 基础处理时间
        
        # 重采样增加时间
        if settings.target_sample_rate and settings.target_sample_rate != metadata.sample_rate:
            base_time *= 1.5
        
        # 格式转换增加时间
        if settings.target_format in [AudioFormat.MP3, AudioFormat.AAC, AudioFormat.OGG]:
            base_time *= 2.0  # 压缩格式需要更多时间
        
        # 效果处理增加时间
        if settings.normalize or settings.trim_silence or settings.fade_in > 0 or settings.fade_out > 0:
            base_time *= 1.3
        
        return max(base_time, 0.5)  # 最少0.5秒


# 全局格式转换器实例
global_format_converter = AudioFormatConverter()
