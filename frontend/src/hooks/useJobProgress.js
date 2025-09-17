import { useState, useEffect, useRef, useCallback } from 'react';
import { audioAPI } from '../services/api';
import ErrorHandler from '../utils/errorHandler';

/**
 * 音频处理进度管理Hook
 */
export const useJobProgress = () => {
  const [jobStatus, setJobStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  
  const pollIntervalRef = useRef(null);
  const abortControllerRef = useRef(null);
  const retryCountRef = useRef(0);
  const maxRetries = 3;

  // 处理阶段映射
  const stageMessages = {
    'PENDING': '等待处理...',
    'ANALYZING': '正在分析音频特征...',
    'FEATURE_EXTRACTION': '正在提取音频特征...',
    'PARAMETER_INVERSION': '正在计算风格参数...',
    'AUDIO_RENDERING': '正在渲染音频...',
    'POST_PROCESSING': '正在后处理...',
    'FINALIZING': '正在完成处理...',
    'COMPLETED': '处理完成',
    'FAILED': '处理失败'
  };

  // 智能轮询间隔计算
  const getPollingInterval = useCallback((currentProgress) => {
    if (currentProgress < 10) return 1000;  // 初期1秒
    if (currentProgress < 50) return 2000;  // 中期2秒
    if (currentProgress < 90) return 1500;  // 后期1.5秒
    return 500; // 接近完成时0.5秒
  }, []);

  // 轮询任务状态
  const pollJobStatus = useCallback(async (jobId) => {
    if (!jobId) return;

    try {
      const status = await audioAPI.getJobStatus(jobId);
      setJobStatus(status);
      
      // 更新进度
      const newProgress = status.progress || 0;
      setProgress(newProgress);
      
      // 重置重试计数
      retryCountRef.current = 0;

      if (status.status === 'COMPLETED') {
        setResult(status);
        setProcessing(false);
        setError(null);
        ErrorHandler.showSuccess('音频处理完成！');
        
        // 清除轮询
        if (pollIntervalRef.current) {
          clearTimeout(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      } else if (status.status === 'FAILED') {
        setError(status.error || '处理失败');
        setProcessing(false);
        ErrorHandler.showError(
          new Error(status.error || '处理失败'), 
          '音频处理'
        );
        
        // 清除轮询
        if (pollIntervalRef.current) {
          clearTimeout(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      } else {
        // 继续轮询，使用智能间隔
        const interval = getPollingInterval(newProgress);
        pollIntervalRef.current = setTimeout(() => {
          pollJobStatus(jobId);
        }, interval);
      }
    } catch (error) {
      console.error('Poll job status error:', error);
      
      // 重试机制
      retryCountRef.current += 1;
      if (retryCountRef.current <= maxRetries) {
        console.log(`Retrying poll (${retryCountRef.current}/${maxRetries})`);
        pollIntervalRef.current = setTimeout(() => {
          pollJobStatus(jobId);
        }, 3000); // 重试时使用3秒间隔
      } else {
        setError('获取任务状态失败');
        setProcessing(false);
        ErrorHandler.showError(error, '获取任务状态');
      }
    }
  }, [getPollingInterval]);

  // 开始处理
  const startProcessing = useCallback(async (jobData) => {
    try {
      setProcessing(true);
      setError(null);
      setProgress(0);
      setResult(null);
      retryCountRef.current = 0;

      // 创建新的AbortController
      abortControllerRef.current = new AbortController();

      // 创建处理任务
      const job = await audioAPI.createJob(jobData);
      
      // 开始轮询任务状态
      pollJobStatus(job.job_id);
      
      return job;
    } catch (error) {
      setError('创建处理任务失败');
      setProcessing(false);
      ErrorHandler.showError(error, '创建处理任务');
      throw error;
    }
  }, [pollJobStatus]);

  // 取消处理
  const cancelProcessing = useCallback(async () => {
    try {
      // 取消网络请求
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // 清除轮询
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }

      // 如果有任务ID，尝试取消服务器端任务
      if (jobStatus?.job_id) {
        try {
          await audioAPI.cancelJob(jobStatus.job_id);
        } catch (error) {
          console.warn('Failed to cancel server job:', error);
        }
      }

      setProcessing(false);
      setJobStatus(null);
      setProgress(0);
      setError(null);
      
      ErrorHandler.showWarning('处理已取消');
    } catch (error) {
      console.error('Cancel processing error:', error);
      ErrorHandler.showError(error, '取消处理');
    }
  }, [jobStatus]);

  // 重置状态
  const resetState = useCallback(() => {
    // 清除轮询
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    // 取消请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setProcessing(false);
    setJobStatus(null);
    setProgress(0);
    setResult(null);
    setError(null);
    retryCountRef.current = 0;
  }, []);

  // 获取当前状态描述
  const getStatusMessage = useCallback(() => {
    if (!jobStatus) return '等待开始';
    return stageMessages[jobStatus.status] || jobStatus.status;
  }, [jobStatus]);

  // 清理资源
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    jobStatus,
    progress,
    processing,
    error,
    result,
    startProcessing,
    cancelProcessing,
    resetState,
    getStatusMessage,
    canCancel: processing && jobStatus?.status !== 'FINALIZING'
  };
};

export default useJobProgress;
