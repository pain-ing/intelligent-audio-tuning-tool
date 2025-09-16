"""
音频流式处理模块 - 内存优化的音频数据处理
实现分块加载、流式处理，避免大文件一次性加载到内存
"""

import numpy as np
import librosa
import soundfile as sf
from typing import Iterator, Tuple, Optional, Dict, Any
import logging
import gc
import psutil
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AudioChunk:
    """音频数据块"""
    data: np.ndarray  # 音频数据 (channels, samples)
    start_sample: int  # 起始采样点
    end_sample: int    # 结束采样点
    sample_rate: int   # 采样率
    is_last: bool = False  # 是否为最后一块

class MemoryAwareAudioLoader:
    """内存感知的音频加载器"""
    
    def __init__(self, max_memory_mb: float = 512.0, dtype: np.dtype = np.float32):
        """
        初始化音频加载器
        
        Args:
            max_memory_mb: 最大内存使用限制 (MB)
            dtype: 音频数据类型，默认float32节省内存
        """
        self.max_memory_mb = max_memory_mb
        self.dtype = dtype
        self.sample_rate = 48000
        
        # 计算自适应块大小
        self._chunk_size = self._calculate_optimal_chunk_size()
        
        logger.info(f"音频加载器初始化: 最大内存={max_memory_mb}MB, 块大小={self._chunk_size}样本")
    
    def _calculate_optimal_chunk_size(self) -> int:
        """计算最优的音频块大小"""
        try:
            # 获取可用内存
            available_memory = psutil.virtual_memory().available / (1024 * 1024)  # MB
            
            # 使用可用内存的一小部分作为单个块的大小
            target_memory_per_chunk = min(self.max_memory_mb, available_memory * 0.1)
            
            # 计算每个样本的内存占用 (假设立体声)
            bytes_per_sample = 2 * np.dtype(self.dtype).itemsize  # 2通道
            samples_per_mb = (1024 * 1024) / bytes_per_sample
            
            # 计算块大小（样本数）
            chunk_samples = int(target_memory_per_chunk * samples_per_mb)
            
            # 确保块大小在合理范围内（1-60秒）
            min_chunk = int(1.0 * self.sample_rate)   # 1秒
            max_chunk = int(60.0 * self.sample_rate)  # 60秒
            
            chunk_samples = max(min_chunk, min(chunk_samples, max_chunk))
            
            logger.info(f"计算得出最优块大小: {chunk_samples}样本 "
                       f"({chunk_samples / self.sample_rate:.1f}秒)")
            
            return chunk_samples
            
        except Exception as e:
            logger.warning(f"无法计算最优块大小，使用默认值: {e}")
            return int(30.0 * self.sample_rate)  # 默认30秒
    
    def get_audio_info(self, file_path: str) -> Dict[str, Any]:
        """获取音频文件信息，不加载数据"""
        try:
            info = sf.info(file_path)
            return {
                "duration": info.duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "frames": info.frames,
                "format": info.format,
                "subtype": info.subtype
            }
        except Exception as e:
            logger.error(f"无法获取音频信息 {file_path}: {e}")
            raise
    
    def load_audio_chunks(self, file_path: str, 
                         overlap_samples: int = None) -> Iterator[AudioChunk]:
        """
        流式加载音频文件，返回音频块迭代器
        
        Args:
            file_path: 音频文件路径
            overlap_samples: 块之间的重叠样本数，用于避免边界效应
            
        Yields:
            AudioChunk: 音频数据块
        """
        if overlap_samples is None:
            overlap_samples = int(0.1 * self.sample_rate)  # 默认100ms重叠
        
        try:
            # 获取音频信息
            audio_info = self.get_audio_info(file_path)
            total_frames = audio_info["frames"]
            original_sr = audio_info["sample_rate"]
            channels = audio_info["channels"]
            
            logger.info(f"开始流式加载音频: {file_path}")
            logger.info(f"音频信息: {audio_info['duration']:.1f}秒, "
                       f"{channels}通道, {original_sr}Hz")
            
            # 计算重采样后的总帧数
            if original_sr != self.sample_rate:
                total_frames_resampled = int(total_frames * self.sample_rate / original_sr)
            else:
                total_frames_resampled = total_frames
            
            # 分块处理
            current_start = 0
            chunk_count = 0
            
            while current_start < total_frames_resampled:
                # 计算当前块的范围
                chunk_end = min(current_start + self._chunk_size, total_frames_resampled)
                
                # 计算在原始采样率下的范围
                if original_sr != self.sample_rate:
                    orig_start = int(current_start * original_sr / self.sample_rate)
                    orig_end = int(chunk_end * original_sr / self.sample_rate)
                else:
                    orig_start = current_start
                    orig_end = chunk_end
                
                # 加载音频块
                try:
                    audio_chunk, sr = librosa.load(
                        file_path,
                        sr=self.sample_rate,
                        mono=False,
                        dtype=self.dtype,
                        offset=orig_start / original_sr,
                        duration=(orig_end - orig_start) / original_sr
                    )
                    
                    # 确保是2D数组 (channels, samples)
                    if audio_chunk.ndim == 1:
                        audio_chunk = audio_chunk.reshape(1, -1)
                    elif audio_chunk.ndim == 2 and audio_chunk.shape[0] > audio_chunk.shape[1]:
                        audio_chunk = audio_chunk.T
                    
                    # 创建音频块对象
                    is_last = (chunk_end >= total_frames_resampled)
                    chunk = AudioChunk(
                        data=audio_chunk,
                        start_sample=current_start,
                        end_sample=current_start + audio_chunk.shape[1],
                        sample_rate=sr,
                        is_last=is_last
                    )
                    
                    chunk_count += 1
                    logger.debug(f"加载音频块 {chunk_count}: "
                               f"{chunk.start_sample}-{chunk.end_sample} "
                               f"({audio_chunk.shape[1]}样本)")
                    
                    yield chunk
                    
                    # 强制垃圾回收，释放内存
                    del audio_chunk
                    if chunk_count % 10 == 0:  # 每10个块进行一次GC
                        gc.collect()
                    
                    if is_last:
                        break
                    
                    # 更新下一块的起始位置（考虑重叠）
                    current_start = chunk_end - overlap_samples
                    
                except Exception as e:
                    logger.error(f"加载音频块失败 {orig_start}-{orig_end}: {e}")
                    break
            
            logger.info(f"音频流式加载完成，共处理 {chunk_count} 个块")
            
        except Exception as e:
            logger.error(f"音频流式加载失败 {file_path}: {e}")
            raise
    
    def load_audio_streaming(self, file_path: str) -> Tuple[Iterator[AudioChunk], Dict[str, Any]]:
        """
        流式加载音频文件，返回块迭代器和音频信息
        
        Returns:
            Tuple[Iterator[AudioChunk], Dict]: (音频块迭代器, 音频信息)
        """
        audio_info = self.get_audio_info(file_path)
        chunks_iterator = self.load_audio_chunks(file_path)
        return chunks_iterator, audio_info

@contextmanager
def memory_efficient_audio_processing(max_memory_mb: float = 512.0):
    """内存高效音频处理上下文管理器"""
    loader = MemoryAwareAudioLoader(max_memory_mb=max_memory_mb)
    
    try:
        yield loader
    finally:
        # 强制垃圾回收
        gc.collect()

class StreamingAudioProcessor:
    """流式音频处理器"""
    
    def __init__(self, max_memory_mb: float = 512.0):
        self.loader = MemoryAwareAudioLoader(max_memory_mb=max_memory_mb)
        self.dtype = np.float32
    
    def process_audio_streaming(self, file_path: str, 
                              processor_func, 
                              output_path: str = None,
                              **kwargs) -> Dict[str, Any]:
        """
        流式处理音频文件
        
        Args:
            file_path: 输入音频文件路径
            processor_func: 处理函数，接收AudioChunk并返回处理后的数据
            output_path: 输出文件路径（可选）
            **kwargs: 传递给处理函数的额外参数
            
        Returns:
            Dict: 处理结果统计
        """
        logger.info(f"开始流式处理音频: {file_path}")
        
        chunks_iterator, audio_info = self.loader.load_audio_streaming(file_path)
        
        processed_chunks = []
        total_processed_samples = 0
        chunk_count = 0
        
        try:
            for chunk in chunks_iterator:
                logger.debug(f"处理音频块 {chunk_count + 1}")
                
                # 应用处理函数
                processed_chunk = processor_func(chunk, **kwargs)
                
                if output_path:
                    processed_chunks.append(processed_chunk)
                
                total_processed_samples += chunk.data.shape[1]
                chunk_count += 1
                
                # 定期进行垃圾回收
                if chunk_count % 5 == 0:
                    gc.collect()
            
            # 如果需要保存输出
            if output_path and processed_chunks:
                self._save_processed_chunks(processed_chunks, output_path, audio_info)
            
            result = {
                "total_chunks": chunk_count,
                "total_samples": total_processed_samples,
                "duration_seconds": total_processed_samples / self.loader.sample_rate,
                "audio_info": audio_info
            }
            
            logger.info(f"流式处理完成: 处理了 {chunk_count} 个块，"
                       f"总计 {total_processed_samples} 个样本")
            
            return result
            
        except Exception as e:
            logger.error(f"流式处理失败: {e}")
            raise
        finally:
            # 清理内存
            del processed_chunks
            gc.collect()
    
    def _save_processed_chunks(self, chunks: list, output_path: str, audio_info: Dict):
        """保存处理后的音频块到文件"""
        try:
            # 合并所有块
            if not chunks:
                return
            
            # 假设所有块具有相同的通道数
            channels = chunks[0].shape[0] if chunks[0].ndim > 1 else 1
            
            # 计算总长度
            total_samples = sum(chunk.shape[-1] for chunk in chunks)
            
            # 创建输出数组
            if channels > 1:
                output_audio = np.zeros((channels, total_samples), dtype=self.dtype)
            else:
                output_audio = np.zeros(total_samples, dtype=self.dtype)
            
            # 复制数据
            current_pos = 0
            for chunk in chunks:
                chunk_samples = chunk.shape[-1]
                if channels > 1:
                    output_audio[:, current_pos:current_pos + chunk_samples] = chunk
                else:
                    output_audio[current_pos:current_pos + chunk_samples] = chunk
                current_pos += chunk_samples
            
            # 保存文件
            sf.write(output_path, output_audio.T if channels > 1 else output_audio, 
                    self.loader.sample_rate)
            
            logger.info(f"已保存处理后的音频到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存音频文件失败: {e}")
            raise

# 便捷函数
def create_streaming_loader(max_memory_mb: float = 512.0) -> MemoryAwareAudioLoader:
    """创建流式音频加载器"""
    return MemoryAwareAudioLoader(max_memory_mb=max_memory_mb)

def create_streaming_processor(max_memory_mb: float = 512.0) -> StreamingAudioProcessor:
    """创建流式音频处理器"""
    return StreamingAudioProcessor(max_memory_mb=max_memory_mb)
