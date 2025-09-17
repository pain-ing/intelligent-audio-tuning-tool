import { message, notification } from 'antd';

/**
 * 统一错误处理工具
 */
export class ErrorHandler {
  static errorMessages = {
    NETWORK_ERROR: '网络连接失败，请检查网络设置',
    UPLOAD_FAILED: '文件上传失败，请重试',
    PROCESSING_FAILED: '音频处理失败，请检查文件格式',
    FILE_TOO_LARGE: '文件过大，请选择小于100MB的文件',
    UNSUPPORTED_FORMAT: '不支持的文件格式，请使用WAV、MP3或FLAC格式',
    SERVER_ERROR: '服务器错误，请稍后重试',
    TIMEOUT: '请求超时，请检查网络连接',
    UNAUTHORIZED: '未授权访问，请重新登录',
    FORBIDDEN: '权限不足，无法执行此操作'
  };

  static solutions = {
    NETWORK_ERROR: [
      '检查网络连接是否正常',
      '尝试刷新页面',
      '检查防火墙设置'
    ],
    UPLOAD_FAILED: [
      '检查文件是否损坏',
      '确认文件格式正确',
      '尝试重新选择文件'
    ],
    PROCESSING_FAILED: [
      '确认音频文件完整且未损坏',
      '检查文件格式是否支持',
      '尝试使用较小的文件'
    ],
    FILE_TOO_LARGE: [
      '压缩音频文件',
      '使用较短的音频片段',
      '降低音频质量'
    ],
    UNSUPPORTED_FORMAT: [
      '转换为WAV、MP3或FLAC格式',
      '使用音频转换工具',
      '检查文件扩展名'
    ]
  };

  /**
   * 处理API错误
   */
  static handleApiError(error, context = '') {
    console.error(`API Error in ${context}:`, error);
    
    let errorCode = 'SERVER_ERROR';
    let errorMessage = this.errorMessages.SERVER_ERROR;
    
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          errorCode = data?.code || 'INVALID_INPUT';
          errorMessage = data?.message || '请求参数错误';
          break;
        case 401:
          errorCode = 'UNAUTHORIZED';
          errorMessage = this.errorMessages.UNAUTHORIZED;
          break;
        case 403:
          errorCode = 'FORBIDDEN';
          errorMessage = this.errorMessages.FORBIDDEN;
          break;
        case 404:
          errorCode = 'NOT_FOUND';
          errorMessage = '请求的资源不存在';
          break;
        case 413:
          errorCode = 'FILE_TOO_LARGE';
          errorMessage = this.errorMessages.FILE_TOO_LARGE;
          break;
        case 415:
          errorCode = 'UNSUPPORTED_FORMAT';
          errorMessage = this.errorMessages.UNSUPPORTED_FORMAT;
          break;
        case 500:
          errorCode = 'SERVER_ERROR';
          errorMessage = this.errorMessages.SERVER_ERROR;
          break;
        case 504:
          errorCode = 'TIMEOUT';
          errorMessage = this.errorMessages.TIMEOUT;
          break;
        default:
          errorMessage = data?.message || `服务器错误 (${status})`;
      }
    } else if (error.request) {
      errorCode = 'NETWORK_ERROR';
      errorMessage = this.errorMessages.NETWORK_ERROR;
    } else {
      errorMessage = error.message || '未知错误';
    }

    return {
      code: errorCode,
      message: errorMessage,
      solutions: this.solutions[errorCode] || ['请联系技术支持']
    };
  }

  /**
   * 显示错误通知
   */
  static showError(error, context = '') {
    const errorInfo = this.handleApiError(error, context);
    
    notification.error({
      message: '操作失败',
      description: (
        <div>
          <div style={{ marginBottom: 8 }}>{errorInfo.message}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            <strong>解决建议：</strong>
            <ul style={{ margin: '4px 0', paddingLeft: '16px' }}>
              {errorInfo.solutions.map((solution, index) => (
                <li key={index}>{solution}</li>
              ))}
            </ul>
          </div>
        </div>
      ),
      duration: 8,
      style: {
        backgroundColor: 'rgba(16, 40, 50, 0.95)',
        border: '1px solid #ff4d4f',
        color: '#B4FFF0'
      }
    });
  }

  /**
   * 显示简单错误消息
   */
  static showSimpleError(error, context = '') {
    const errorInfo = this.handleApiError(error, context);
    message.error(errorInfo.message);
  }

  /**
   * 显示成功消息
   */
  static showSuccess(message) {
    notification.success({
      message: '操作成功',
      description: message,
      duration: 4,
      style: {
        backgroundColor: 'rgba(16, 40, 50, 0.95)',
        border: '1px solid #52c41a',
        color: '#B4FFF0'
      }
    });
  }

  /**
   * 显示警告消息
   */
  static showWarning(message) {
    notification.warning({
      message: '注意',
      description: message,
      duration: 6,
      style: {
        backgroundColor: 'rgba(16, 40, 50, 0.95)',
        border: '1px solid #fa8c16',
        color: '#B4FFF0'
      }
    });
  }
}

export default ErrorHandler;
