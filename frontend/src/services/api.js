import axios from 'axios';

// 创建 axios 实例
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8080',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    // const token = localStorage.getItem('token');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      // 服务器返回错误状态码
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // 未授权，可能需要重新登录
          console.error('Unauthorized access');
          break;
        case 403:
          // 禁止访问
          console.error('Forbidden access');
          break;
        case 404:
          // 资源不存在
          console.error('Resource not found');
          break;
        case 500:
          // 服务器内部错误
          console.error('Internal server error');
          break;
        default:
          console.error('API Error:', data?.message || error.message);
      }
      
      return Promise.reject(data || error.message);
    } else if (error.request) {
      // 网络错误
      console.error('Network error:', error.message);
      return Promise.reject('网络连接失败，请检查网络设置');
    } else {
      // 其他错误
      console.error('Error:', error.message);
      return Promise.reject(error.message);
    }
  }
);

// API 方法
export const audioAPI = {
  // 健康检查
  healthCheck: () => api.get('/health'),

  // 获取上传签名
  getUploadSignature: (contentType, extension) => 
    api.post('/uploads/sign', { content_type: contentType, extension }),

  // 创建处理任务
  createJob: (jobData) => 
    api.post('/jobs', jobData),

  // 获取任务状态
  getJobStatus: (jobId) => 
    api.get(`/jobs/${jobId}`),

  // 重试任务
  retryJob: (jobId) => 
    api.post(`/jobs/${jobId}/retry`),

  // 预设管理
  getPresets: (params = {}) => 
    api.get('/presets', { params }),

  createPreset: (presetData) => 
    api.post('/presets', presetData),

  updatePreset: (presetId, presetData) => 
    api.put(`/presets/${presetId}`, presetData),

  deletePreset: (presetId) => 
    api.delete(`/presets/${presetId}`),

  // 获取预设详情
  getPreset: (presetId) => 
    api.get(`/presets/${presetId}`),
};

// 文件上传相关
export const uploadAPI = {
  // 直接上传到对象存储
  uploadToStorage: async (file, signedUrl, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return axios.put(signedUrl, file, {
      headers: {
        'Content-Type': file.type,
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
  },

  // 分片上传（大文件）
  uploadLargeFile: async (file, signedUrls, onProgress) => {
    const chunkSize = 5 * 1024 * 1024; // 5MB per chunk
    const chunks = Math.ceil(file.size / chunkSize);
    const uploadPromises = [];

    for (let i = 0; i < chunks; i++) {
      const start = i * chunkSize;
      const end = Math.min(start + chunkSize, file.size);
      const chunk = file.slice(start, end);
      
      const uploadPromise = axios.put(signedUrls[i], chunk, {
        headers: {
          'Content-Type': 'application/octet-stream',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress) {
            const chunkProgress = (progressEvent.loaded / progressEvent.total) * 100;
            const totalProgress = ((i * 100) + chunkProgress) / chunks;
            onProgress(Math.round(totalProgress));
          }
        },
      });

      uploadPromises.push(uploadPromise);
    }

    return Promise.all(uploadPromises);
  },
};

// WebSocket 连接（用于实时状态更新）
export class AudioWebSocket {
  constructor(jobId, onMessage, onError) {
    this.jobId = jobId;
    this.onMessage = onMessage;
    this.onError = onError;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8080'}/ws/jobs/${this.jobId}`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (this.onError) {
          this.onError(error);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      if (this.onError) {
        this.onError(error);
      }
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.pow(2, this.reconnectAttempts) * 1000; // 指数退避
      
      console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      if (this.onError) {
        this.onError(new Error('WebSocket connection failed after multiple attempts'));
      }
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }
}

// 导出默认 API 实例
export default api;
