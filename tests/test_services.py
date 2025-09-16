"""
服务层测试
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch

from src.services.audio_service import AudioService
from src.services.job_service import JobService
from src.services.storage_service import LocalStorageService, MinIOStorageService
from src.services.cache_service import LocalCacheService
from src.core.exceptions import AudioProcessingError, StorageError
from tests.conftest import assert_audio_features_valid, assert_style_params_valid, assert_metrics_valid


class TestAudioService:
    """音频服务测试"""
    
    @pytest.mark.asyncio
    async def test_analyze_features_success(self, sample_audio_file):
        """测试音频特征分析成功"""
        service = AudioService()
        
        with patch('src.services.audio_service.AudioService._analyze_features_sync') as mock_analyze:
            mock_analyze.return_value = {
                "stft": {"features": {"win_2048": {"spectral_centroid": 1000}}},
                "mel": {"mean": -30, "std": 10},
                "lufs": {"integrated_lufs": -23.0},
                "true_peak_db": -3.0,
                "f0": {"mean_f0": 440, "voiced_ratio": 0.8},
                "stereo": {"is_stereo": True, "width": 1.0},
                "reverb": {"rt60_estimate": 0.5},
                "audio_info": {"duration_seconds": 10.0, "channels": 2, "sample_rate": 48000}
            }
            
            features = await service.analyze_features(sample_audio_file)
            assert_audio_features_valid(features)
            mock_analyze.assert_called_once_with(sample_audio_file)
    
    @pytest.mark.asyncio
    async def test_analyze_features_file_not_found(self):
        """测试分析不存在的文件"""
        service = AudioService()
        
        with pytest.raises(AudioProcessingError):
            await service.analyze_features("nonexistent_file.wav")
    
    @pytest.mark.asyncio
    async def test_invert_parameters_success(self, sample_features):
        """测试参数反演成功"""
        service = AudioService()
        
        with patch('src.services.audio_service.AudioService._invert_parameters_sync') as mock_invert:
            mock_invert.return_value = {
                "eq": {"bands": [{"freq": 1000, "gain": 2.0, "q": 1.0}]},
                "dynamics": {"compressor": {"ratio": 4.0, "threshold": -20.0}},
                "reverb": {"ir_params": {"room_size": 0.5}},
                "stereo": {"width": 1.2},
                "pitch": {"semitones": 0.0}
            }
            
            params = await service.invert_parameters(sample_features, sample_features, "A")
            assert_style_params_valid(params)
            mock_invert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_render_audio_success(self, temp_dir, sample_style_params):
        """测试音频渲染成功"""
        service = AudioService()
        
        input_path = os.path.join(temp_dir, "input.wav")
        output_path = os.path.join(temp_dir, "output.wav")
        
        # 创建虚拟输入文件
        with open(input_path, 'wb') as f:
            f.write(b'fake audio data')
        
        with patch('src.services.audio_service.AudioService._render_audio_sync') as mock_render:
            mock_render.return_value = {
                "stft_dist": 0.1,
                "mel_dist": 0.05,
                "lufs_err": 0.5,
                "tp_db": -1.0,
                "artifacts_rate": 0.01
            }
            
            # 创建虚拟输出文件
            with open(output_path, 'wb') as f:
                f.write(b'fake rendered audio')
            
            metrics = await service.render_audio(input_path, output_path, sample_style_params)
            assert_metrics_valid(metrics)
            mock_render.assert_called_once()


class TestJobService:
    """任务服务测试"""
    
    @pytest.mark.asyncio
    async def test_create_job_success(self, test_db, sample_job_data):
        """测试创建任务成功"""
        service = JobService(test_db)
        
        with patch('src.services.job_service.JobService._create_job_record') as mock_create:
            mock_create.return_value = sample_job_data
            
            result = await service.create_job("ref_key", "tgt_key", "A")
            
            assert result["id"] == sample_job_data["id"]
            assert result["status"] == "PENDING"
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_success(self, test_db, sample_job_data):
        """测试获取任务成功"""
        service = JobService(test_db)
        
        with patch('src.services.job_service.JobService._get_job_record') as mock_get:
            mock_get.return_value = sample_job_data
            
            job = await service.get_job(sample_job_data["id"])
            
            assert job["id"] == sample_job_data["id"]
            assert job["status"] == sample_job_data["status"]
            mock_get.assert_called_once_with(sample_job_data["id"])
    
    @pytest.mark.asyncio
    async def test_list_jobs_success(self, test_db):
        """测试列出任务成功"""
        service = JobService(test_db)
        
        with patch('src.services.job_service.JobService._list_job_records') as mock_list:
            mock_list.return_value = {
                "jobs": [{"id": "job1", "status": "COMPLETED"}],
                "total": 1,
                "has_more": False
            }
            
            result = await service.list_jobs(limit=10, offset=0)
            
            assert len(result["jobs"]) == 1
            assert result["total"] == 1
            assert not result["has_more"]
            mock_list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(self, test_db, sample_job_data):
        """测试取消任务成功"""
        service = JobService(test_db)
        
        with patch('src.services.job_service.JobService._update_job_status') as mock_update:
            mock_update.return_value = True
            
            result = await service.cancel_job(sample_job_data["id"])
            
            assert result["status"] == "success"
            mock_update.assert_called_once()


class TestStorageService:
    """存储服务测试"""
    
    @pytest.mark.asyncio
    async def test_local_storage_upload_download(self, temp_dir):
        """测试本地存储上传下载"""
        service = LocalStorageService()
        service.base_path = temp_dir
        
        # 创建测试文件
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # 上传文件
        object_key = "uploads/test.txt"
        await service.upload_file(test_file, object_key)

        # 验证文件存在
        uploaded_path = service._get_full_path(object_key)
        assert os.path.exists(uploaded_path)
        
        # 下载文件
        download_path = os.path.join(temp_dir, "downloaded.txt")
        await service.download_file(object_key, download_path)

        # 验证内容
        with open(download_path, 'r') as f:
            content = f.read()
        assert content == "test content"
    
    @pytest.mark.asyncio
    async def test_local_storage_delete(self, temp_dir):
        """测试本地存储删除"""
        service = LocalStorageService()
        service.base_path = temp_dir
        
        # 创建测试文件
        object_key = "test/delete_me.txt"
        full_path = service._get_full_path(object_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write("delete me")
        
        # 删除文件
        await service.delete_file(object_key)

        # 验证文件不存在
        assert not os.path.exists(full_path)
    
    @pytest.mark.asyncio
    async def test_minio_storage_mock(self):
        """测试MinIO存储（模拟）"""
        with patch('src.services.storage_service.Minio') as mock_minio_class:
            mock_client = Mock()
            mock_minio_class.return_value = mock_client
            
            service = MinIOStorageService()
            
            # 测试上传
            mock_client.fput_object.return_value = None
            await service.upload_file("local_file.txt", "remote_key.txt")
            mock_client.fput_object.assert_called_once()
            
            # 测试下载
            mock_client.fget_object.return_value = None
            await service.download_file("remote_key.txt", "local_file.txt")
            mock_client.fget_object.assert_called_once()


class TestCacheService:
    """缓存服务测试"""
    
    @pytest.mark.asyncio
    async def test_local_cache_operations(self):
        """测试本地缓存操作"""
        service = LocalCacheService()
        
        # 测试设置和获取
        await service.set("test_key", "test_value", ttl=60)
        value = await service.get("test_key")
        assert value == "test_value"
        
        # 测试存在性检查
        exists = await service.exists("test_key")
        assert exists is True
        
        # 测试删除
        await service.delete("test_key")
        value = await service.get("test_key")
        assert value is None
        
        exists = await service.exists("test_key")
        assert exists is False
    
    @pytest.mark.asyncio
    async def test_local_cache_expiration(self):
        """测试本地缓存过期"""
        service = LocalCacheService()
        
        # 设置短TTL
        await service.set("expire_key", "expire_value", ttl=0.1)
        
        # 立即获取应该成功
        value = await service.get("expire_key")
        assert value == "expire_value"
        
        # 等待过期
        import asyncio
        await asyncio.sleep(0.2)
        
        # 获取应该返回None
        value = await service.get("expire_key")
        assert value is None
