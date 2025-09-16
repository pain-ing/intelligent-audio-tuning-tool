"""
统一异常处理模块
"""
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """错误代码枚举"""
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    
    # 文件相关错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    
    # 音频处理错误
    AUDIO_ANALYSIS_FAILED = "AUDIO_ANALYSIS_FAILED"
    PARAMETER_INVERSION_FAILED = "PARAMETER_INVERSION_FAILED"
    AUDIO_RENDERING_FAILED = "AUDIO_RENDERING_FAILED"
    
    # 任务相关错误
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_FAILED = "JOB_FAILED"
    
    # 存储相关错误
    STORAGE_ERROR = "STORAGE_ERROR"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"


class AudioTunerException(Exception):
    """基础异常类"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        detail: Optional[Dict[str, Any]] = None,
        status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.detail = detail or {}
        self.status_code = status_code
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "code": self.code.value,
            "message": self.message
        }
        if self.detail:
            result["detail"] = self.detail
        return result


class ValidationError(AudioTunerException):
    """输入验证错误"""
    
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_INPUT,
            detail=detail,
            status_code=400
        )


class NotFoundError(AudioTunerException):
    """资源未找到错误"""
    
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            detail=detail,
            status_code=404
        )


class FileError(AudioTunerException):
    """文件相关错误"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.FILE_NOT_FOUND,
        detail: Optional[Dict[str, Any]] = None
    ):
        status_code = 400 if code in [ErrorCode.FILE_TOO_LARGE, ErrorCode.UNSUPPORTED_FORMAT] else 404
        super().__init__(
            message=message,
            code=code,
            detail=detail,
            status_code=status_code
        )


class AudioProcessingError(AudioTunerException):
    """音频处理错误"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.AUDIO_ANALYSIS_FAILED,
        detail: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            detail=detail,
            status_code=500
        )


class JobError(AudioTunerException):
    """任务相关错误"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.JOB_NOT_FOUND,
        detail: Optional[Dict[str, Any]] = None
    ):
        status_code = 404 if code == ErrorCode.JOB_NOT_FOUND else 400
        super().__init__(
            message=message,
            code=code,
            detail=detail,
            status_code=status_code
        )


class StorageError(AudioTunerException):
    """存储相关错误"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.STORAGE_ERROR,
        detail: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            detail=detail,
            status_code=500
        )
