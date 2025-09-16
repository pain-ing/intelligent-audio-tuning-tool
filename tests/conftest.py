"""
测试配置和夹具
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import DesktopConfig
from src.core.container import ServiceScope
from src.services.base import StorageServiceInterface, CacheServiceInterface, AudioProcessorInterface


@pytest.fixture
def temp_dir():
    """临时目录夹具"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def test_config():
    """测试配置"""
    config = DesktopConfig()
    config.debug = True
    config.database_url = "sqlite:///:memory:"
    config.storage_mode = "local"
    config.cache_mode = "local"
    return config


@pytest.fixture
def mock_storage_service():
    """模拟存储服务"""
    mock = Mock(spec=StorageServiceInterface)
    mock.upload_file = AsyncMock(return_value="test_key")
    mock.download_file = AsyncMock()
    mock.delete_file = AsyncMock()
    mock.get_download_url = AsyncMock(return_value="http://test.com/file")
    return mock


@pytest.fixture
def mock_cache_service():
    """模拟缓存服务"""
    mock = Mock(spec=CacheServiceInterface)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def mock_audio_service():
    """模拟音频服务"""
    mock = Mock(spec=AudioProcessorInterface)
    mock.analyze_features = AsyncMock(return_value={
        "stft": {"features": {"win_2048": {"spectral_centroid": 1000}}},
        "mel": {"mean": -30, "std": 10},
        "lufs": {"integrated_lufs": -23.0},
        "true_peak_db": -3.0,
        "f0": {"mean_f0": 440, "voiced_ratio": 0.8},
        "stereo": {"is_stereo": True, "width": 1.0},
        "reverb": {"rt60_estimate": 0.5},
        "audio_info": {"duration_seconds": 10.0, "channels": 2, "sample_rate": 48000}
    })
    mock.invert_parameters = AsyncMock(return_value={
        "eq": {"bands": [{"freq": 1000, "gain": 2.0, "q": 1.0}]},
        "dynamics": {"compressor": {"ratio": 4.0, "threshold": -20.0}},
        "reverb": {"ir_params": {"room_size": 0.5}},
        "stereo": {"width": 1.2},
        "pitch": {"semitones": 0.0}
    })
    mock.render_audio = AsyncMock(return_value={
        "stft_dist": 0.1,
        "mel_dist": 0.05,
        "lufs_err": 0.5,
        "tp_db": -1.0,
        "artifacts_rate": 0.01
    })
    return mock


@pytest.fixture
def test_db():
    """测试数据库"""
    engine = create_engine("sqlite:///:memory:")
    
    # 创建表
    try:
        from api.app.models_sqlite import Base
        Base.metadata.create_all(engine)
    except ImportError:
        # 如果模型不存在，跳过
        pass
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def service_scope(mock_storage_service, mock_cache_service, mock_audio_service):
    """服务作用域夹具"""
    with ServiceScope(
        storage_service=mock_storage_service,
        cache_service=mock_cache_service,
        audio_service=mock_audio_service
    ) as scope:
        yield scope


@pytest.fixture
def sample_audio_file(temp_dir):
    """示例音频文件"""
    import numpy as np
    import soundfile as sf
    
    # 生成简单的正弦波
    sample_rate = 48000
    duration = 1.0  # 1秒
    frequency = 440  # A4音符
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    file_path = os.path.join(temp_dir, "test_audio.wav")
    sf.write(file_path, audio_data, sample_rate)
    
    return file_path


@pytest.fixture
def sample_job_data():
    """示例任务数据"""
    return {
        "id": "test-job-123",
        "mode": "A",
        "ref_key": "uploads/ref_audio.wav",
        "tgt_key": "uploads/tgt_audio.wav",
        "status": "PENDING",
        "progress": 0
    }


@pytest.fixture
def sample_features():
    """示例音频特征"""
    return {
        "stft": {
            "features": {
                "win_2048": {
                    "spectral_centroid": 1500.0,
                    "spectral_bandwidth": 800.0,
                    "spectral_rolloff": 3000.0
                }
            }
        },
        "mel": {
            "mean": -25.0,
            "std": 12.0,
            "features": [0.1, 0.2, 0.3, 0.4, 0.5]
        },
        "lufs": {
            "integrated_lufs": -18.0,
            "short_term_lufs": [-20.0, -19.0, -18.0, -17.0]
        },
        "true_peak_db": -2.5,
        "f0": {
            "mean_f0": 220.0,
            "voiced_ratio": 0.75,
            "f0_contour": [220, 225, 218, 222]
        },
        "stereo": {
            "is_stereo": True,
            "width": 0.8,
            "correlation": 0.9
        },
        "reverb": {
            "rt60_estimate": 0.8,
            "reverb_presence": 0.3
        },
        "audio_info": {
            "duration_seconds": 5.0,
            "channels": 2,
            "sample_rate": 48000,
            "samples": 240000
        }
    }


@pytest.fixture
def sample_style_params():
    """示例风格参数"""
    return {
        "eq": {
            "bands": [
                {"freq": 100, "gain": 1.5, "q": 0.7},
                {"freq": 1000, "gain": -2.0, "q": 1.0},
                {"freq": 5000, "gain": 3.0, "q": 1.5}
            ]
        },
        "dynamics": {
            "compressor": {
                "ratio": 3.0,
                "threshold": -18.0,
                "attack": 10.0,
                "release": 100.0
            },
            "limiter": {
                "threshold": -1.0,
                "release": 50.0
            }
        },
        "reverb": {
            "ir_params": {
                "room_size": 0.6,
                "damping": 0.4,
                "wet_level": 0.2
            }
        },
        "stereo": {
            "width": 1.1
        },
        "pitch": {
            "semitones": 0.5
        }
    }


# 测试工具函数
def assert_audio_features_valid(features):
    """验证音频特征格式"""
    required_keys = ["stft", "mel", "lufs", "true_peak_db", "f0", "stereo", "reverb", "audio_info"]
    for key in required_keys:
        assert key in features, f"Missing required feature: {key}"
    
    # 验证音频信息
    audio_info = features["audio_info"]
    assert audio_info["sample_rate"] > 0
    assert audio_info["duration_seconds"] > 0
    assert audio_info["channels"] in [1, 2]


def assert_style_params_valid(params):
    """验证风格参数格式"""
    required_keys = ["eq", "dynamics", "reverb", "stereo", "pitch"]
    for key in required_keys:
        assert key in params, f"Missing required parameter: {key}"


def assert_metrics_valid(metrics):
    """验证处理指标格式"""
    required_keys = ["stft_dist", "mel_dist", "lufs_err", "tp_db", "artifacts_rate"]
    for key in required_keys:
        assert key in metrics, f"Missing required metric: {key}"
        assert isinstance(metrics[key], (int, float)), f"Metric {key} should be numeric"
