"""
类型定义和注解
"""
from typing import Dict, List, Any, Optional, Union, Tuple, Protocol, TypeVar, Generic
from typing_extensions import TypedDict, Literal
from enum import Enum
import numpy as np
from dataclasses import dataclass


# 基础类型别名
AudioArray = np.ndarray
FrequencyHz = float
TimeSeconds = float
DecibelValue = float
SampleRate = int
ChannelCount = int


# 音频信息类型
class AudioInfo(TypedDict):
    """音频文件信息"""
    duration_seconds: TimeSeconds
    channels: ChannelCount
    sample_rate: SampleRate
    samples: int


# 音频特征类型
class STFTFeatures(TypedDict):
    """STFT特征"""
    features: Dict[str, Dict[str, float]]


class MelFeatures(TypedDict):
    """Mel频谱特征"""
    mean: float
    std: float
    features: Optional[List[float]]


class LUFSFeatures(TypedDict):
    """LUFS响度特征"""
    integrated_lufs: DecibelValue
    short_term_lufs: Optional[List[DecibelValue]]


class F0Features(TypedDict):
    """基频特征"""
    mean_f0: FrequencyHz
    voiced_ratio: float
    f0_contour: Optional[List[FrequencyHz]]


class StereoFeatures(TypedDict):
    """立体声特征"""
    is_stereo: bool
    width: float
    correlation: Optional[float]


class ReverbFeatures(TypedDict):
    """混响特征"""
    rt60_estimate: TimeSeconds
    reverb_presence: Optional[float]


class AudioFeatures(TypedDict):
    """完整音频特征"""
    stft: STFTFeatures
    mel: MelFeatures
    lufs: LUFSFeatures
    true_peak_db: DecibelValue
    f0: F0Features
    stereo: StereoFeatures
    reverb: ReverbFeatures
    audio_info: AudioInfo


# 风格参数类型
class EQBand(TypedDict):
    """均衡器频段"""
    freq: FrequencyHz
    gain: DecibelValue
    q: float


class EQParams(TypedDict):
    """均衡器参数"""
    bands: List[EQBand]


class CompressorParams(TypedDict):
    """压缩器参数"""
    ratio: float
    threshold: DecibelValue
    attack: TimeSeconds
    release: TimeSeconds


class LimiterParams(TypedDict):
    """限制器参数"""
    threshold: DecibelValue
    release: TimeSeconds


class DynamicsParams(TypedDict):
    """动态处理参数"""
    compressor: CompressorParams
    limiter: Optional[LimiterParams]


class ReverbParams(TypedDict):
    """混响参数"""
    ir_params: Dict[str, float]


class StereoParams(TypedDict):
    """立体声参数"""
    width: float


class PitchParams(TypedDict):
    """音调参数"""
    semitones: float


class StyleParams(TypedDict):
    """风格参数"""
    eq: EQParams
    dynamics: DynamicsParams
    reverb: ReverbParams
    stereo: StereoParams
    pitch: PitchParams


# 处理指标类型
class ProcessingMetrics(TypedDict):
    """处理指标"""
    stft_dist: float
    mel_dist: float
    lufs_err: DecibelValue
    tp_db: DecibelValue
    artifacts_rate: float


# 任务状态枚举
class JobStatus(str, Enum):
    """任务状态"""
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    INVERTING = "INVERTING"
    RENDERING = "RENDERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcessingMode(str, Enum):
    """处理模式"""
    MODE_A = "A"  # 配对模式
    MODE_B = "B"  # 风格模式


# 任务数据类型
@dataclass
class JobData:
    """任务数据"""
    id: str
    mode: ProcessingMode
    ref_key: str
    tgt_key: str
    status: JobStatus
    progress: int
    created_at: str
    updated_at: Optional[str] = None
    result_key: Optional[str] = None
    error: Optional[str] = None
    metrics: Optional[ProcessingMetrics] = None


# 协议定义
class AudioProcessor(Protocol):
    """音频处理器协议"""
    
    async def analyze_features(self, file_path: str) -> AudioFeatures:
        """分析音频特征"""
        ...
    
    async def invert_parameters(
        self,
        ref_features: AudioFeatures,
        tgt_features: AudioFeatures,
        mode: ProcessingMode
    ) -> StyleParams:
        """反演风格参数"""
        ...
    
    async def render_audio(
        self,
        input_path: str,
        output_path: str,
        style_params: StyleParams
    ) -> ProcessingMetrics:
        """渲染音频"""
        ...


class StorageProvider(Protocol):
    """存储提供者协议"""
    
    async def upload_file(self, local_path: str, object_key: str) -> str:
        """上传文件"""
        ...
    
    async def download_file(self, object_key: str, local_path: str) -> None:
        """下载文件"""
        ...
    
    async def delete_file(self, object_key: str) -> None:
        """删除文件"""
        ...
    
    async def get_download_url(self, object_key: str, expires: int = 3600) -> str:
        """获取下载URL"""
        ...


class CacheProvider(Protocol):
    """缓存提供者协议"""
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        ...
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        ...
    
    async def delete(self, key: str) -> None:
        """删除缓存值"""
        ...
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        ...


# 泛型类型
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class Repository(Protocol, Generic[T]):
    """仓储协议"""
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        ...
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """根据ID获取实体"""
        ...
    
    async def update(self, entity: T) -> T:
        """更新实体"""
        ...
    
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        ...
    
    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[T], int]:
        """列出实体"""
        ...


# 响应类型
class APIResponse(TypedDict, Generic[T]):
    """API响应"""
    success: bool
    data: Optional[T]
    error: Optional[str]
    message: Optional[str]


class PaginatedResponse(TypedDict, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool


# 配置类型
class DatabaseConfig(TypedDict):
    """数据库配置"""
    url: str
    pool_size: int
    max_overflow: int
    pool_timeout: int


class StorageConfig(TypedDict):
    """存储配置"""
    mode: Literal["local", "minio"]
    bucket: str
    endpoint: Optional[str]
    access_key: Optional[str]
    secret_key: Optional[str]
    base_path: Optional[str]


class CacheConfig(TypedDict):
    """缓存配置"""
    mode: Literal["local", "redis", "disabled"]
    url: Optional[str]
    ttl: int


class AppConfig(TypedDict):
    """应用配置"""
    name: str
    version: str
    mode: Literal["cloud", "desktop"]
    debug: bool
    host: str
    port: int
    database: DatabaseConfig
    storage: StorageConfig
    cache: CacheConfig


# 事件类型
class Event(TypedDict):
    """事件"""
    type: str
    timestamp: float
    data: Dict[str, Any]


class JobEvent(Event):
    """任务事件"""
    job_id: str
    status: JobStatus
    progress: int


# 错误类型
class ErrorDetail(TypedDict):
    """错误详情"""
    code: str
    message: str
    field: Optional[str]
    details: Optional[Dict[str, Any]]


# 文件类型
SupportedAudioFormat = Literal[
    "wav", "mp3", "flac", "aac", "ogg", "m4a", "wma"
]


class FileInfo(TypedDict):
    """文件信息"""
    filename: str
    size: int
    format: SupportedAudioFormat
    object_key: str
    upload_time: str
