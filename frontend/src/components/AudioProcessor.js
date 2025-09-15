import React, { useState, useCallback } from 'react';
import {
  Row, Col, Card, Button, Progress, Alert, Space, Typography,
  Radio, Divider, message, Spin
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined, DownloadOutlined,
  SyncOutlined, CheckCircleOutlined, ExclamationCircleOutlined
} from '@ant-design/icons';
import FileUploader from './FileUploader';
import AudioPlayer from './AudioPlayer';
import VisualizationPanel from './VisualizationPanel';
import ParameterEditor from './ParameterEditor';
import { audioAPI, uploadAPI } from '../services/api';

const { Title, Text } = Typography;

const AudioProcessor = () => {
  const [mode, setMode] = useState('A');
  const [referenceFile, setReferenceFile] = useState(null);
  const [targetFile, setTargetFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // 文件上传处理
  const handleReferenceUpload = useCallback(async (file) => {
    try {
      const uploadInfo = await audioAPI.getUploadSignature(file.type, '.wav');
      // 直接上传到对象存储
      await uploadAPI.uploadToStorage(file, uploadInfo.upload_url);
      // 保存文件信息（使用对象键）
      setReferenceFile({
        name: file.name,
        key: uploadInfo.object_key,
        file: file
      });
      message.success('参考音频上传成功');
    } catch (error) {
      message.error('参考音频上传失败');
    }
  }, []);

  const handleTargetUpload = useCallback(async (file) => {
    try {
      const uploadInfo = await audioAPI.getUploadSignature(file.type, '.wav');
      // 直接上传到对象存储
      await uploadAPI.uploadToStorage(file, uploadInfo.upload_url);
      setTargetFile({
        name: file.name,
        key: uploadInfo.object_key,
        file: file
      });
      message.success('目标音频上传成功');
    } catch (error) {
      message.error('目标音频上传失败');
    }
  }, []);

  // 开始处理
  const handleStartProcessing = async () => {
    if (!referenceFile || !targetFile) {
      message.error('请先上传参考音频和目标音频');
      return;
    }

    try {
      setProcessing(true);
      setError(null);
      setProgress(0);

      // 创建处理任务
      const job = await audioAPI.createJob({
        mode,
        ref_key: referenceFile.key,
        tgt_key: targetFile.key
      });

      setJobId(job.job_id);
      
      // 开始轮询任务状态
      pollJobStatus(job.job_id);
      
    } catch (error) {
      setError('处理任务创建失败');
      setProcessing(false);
    }
  };

  // 轮询任务状态
  const pollJobStatus = async (id) => {
    try {
      const status = await audioAPI.getJobStatus(id);
      setJobStatus(status);
      setProgress(status.progress || 0);

      if (status.status === 'COMPLETED') {
        setResult(status);
        setProcessing(false);
        message.success('音频处理完成！');
      } else if (status.status === 'FAILED') {
        setError(status.error || '处理失败');
        setProcessing(false);
      } else {
        // 继续轮询
        setTimeout(() => pollJobStatus(id), 2000);
      }
    } catch (error) {
      setError('获取任务状态失败');
      setProcessing(false);
    }
  };

  // 下载结果
  const handleDownload = () => {
    if (result?.download_url) {
      window.open(result.download_url, '_blank');
    }
  };

  // 重置状态
  const handleReset = () => {
    setReferenceFile(null);
    setTargetFile(null);
    setProcessing(false);
    setJobId(null);
    setJobStatus(null);
    setProgress(0);
    setResult(null);
    setError(null);
  };

  const getStatusIcon = () => {
    if (processing) return <SyncOutlined spin />;
    if (result) return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    if (error) return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
    return null;
  };

  const getStatusText = () => {
    if (processing) {
      switch (jobStatus?.status) {
        case 'ANALYZING': return '正在分析音频特征...';
        case 'INVERTING': return '正在计算风格参数...';
        case 'RENDERING': return '正在渲染音频...';
        default: return '正在处理...';
      }
    }
    if (result) return '处理完成';
    if (error) return '处理失败';
    return '等待开始';
  };

  return (
    <div className="audio-processor">
      {/* 模式选择 */}
      <Card title="处理模式" style={{ marginBottom: 24 }}>
        <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
          <Space direction="vertical">
            <Radio value="A">
              <strong>A 模式 - 配对模式</strong>
              <br />
              <Text type="secondary">
                参考音频和目标音频是同一素材的不同版本，系统会进行时间对齐和精确匹配
              </Text>
            </Radio>
            <Radio value="B">
              <strong>B 模式 - 风格模式</strong>
              <br />
              <Text type="secondary">
                参考音频和目标音频是不同素材，系统会学习参考音频的风格特征并应用到目标音频
              </Text>
            </Radio>
          </Space>
        </Radio.Group>
      </Card>

      {/* 文件上传 */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={12}>
          <Card title="参考音频" className="upload-card">
            <FileUploader
              onFileSelect={handleReferenceUpload}
              accept="audio/*"
              title="上传参考音频"
              description="已经过调音处理的音频文件"
              file={referenceFile}
            />
            {referenceFile && (
              <AudioPlayer 
                file={referenceFile.file}
                title="参考音频"
              />
            )}
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="目标音频" className="upload-card">
            <FileUploader
              onFileSelect={handleTargetUpload}
              accept="audio/*"
              title="上传目标音频"
              description="需要调音处理的原始音频文件"
              file={targetFile}
            />
            {targetFile && (
              <AudioPlayer 
                file={targetFile.file}
                title="目标音频"
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 处理控制 */}
      <Card style={{ marginTop: 24 }}>
        <div style={{ textAlign: 'center' }}>
          <Space size="large" direction="vertical" style={{ width: '100%' }}>
            <div>
              <Button
                type="primary"
                size="large"
                onClick={handleStartProcessing}
                disabled={!referenceFile || !targetFile || processing}
                loading={processing}
                style={{ minWidth: 120 }}
              >
                {processing ? '处理中...' : '开始处理'}
              </Button>
              
              {(result || error) && (
                <Button
                  style={{ marginLeft: 16 }}
                  onClick={handleReset}
                >
                  重新开始
                </Button>
              )}
            </div>

            {/* 状态显示 */}
            {(processing || result || error) && (
              <div>
                <Space align="center">
                  {getStatusIcon()}
                  <Text>{getStatusText()}</Text>
                </Space>
                
                {processing && (
                  <Progress 
                    percent={progress} 
                    style={{ marginTop: 16, maxWidth: 400 }}
                    strokeColor={{
                      '0%': '#108ee9',
                      '100%': '#87d068',
                    }}
                  />
                )}
              </div>
            )}

            {/* 错误信息 */}
            {error && (
              <Alert
                message="处理失败"
                description={error}
                type="error"
                showIcon
                style={{ maxWidth: 500 }}
              />
            )}

            {/* 成功结果 */}
            {result && (
              <Alert
                message="处理完成"
                description="音频调音处理已完成，您可以下载结果或查看详细信息"
                type="success"
                showIcon
                action={
                  <Button size="small" onClick={handleDownload}>
                    <DownloadOutlined /> 下载结果
                  </Button>
                }
                style={{ maxWidth: 500 }}
              />
            )}
          </Space>
        </div>
      </Card>

      {/* 结果展示 */}
      {result && (
        <>
          <Divider>处理结果</Divider>
          
          {/* AB 对比播放 */}
          <Card title="AB 对比播放" style={{ marginTop: 24 }}>
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={12}>
                <div className="ab-section">
                  <Title level={5}>原始音频</Title>
                  <AudioPlayer 
                    file={targetFile.file}
                    title="目标音频（处理前）"
                  />
                </div>
              </Col>
              <Col xs={24} lg={12}>
                <div className="ab-section">
                  <Title level={5}>处理后音频</Title>
                  <AudioPlayer 
                    url={result.download_url}
                    title="处理后音频"
                  />
                </div>
              </Col>
            </Row>
          </Card>

          {/* 可视化面板 */}
          <VisualizationPanel 
            jobStatus={result}
            style={{ marginTop: 24 }}
          />

          {/* 参数编辑器 */}
          <ParameterEditor 
            parameters={result.style_params}
            onParametersChange={(params) => {
              // 处理参数变更
              console.log('Parameters changed:', params);
            }}
            style={{ marginTop: 24 }}
          />
        </>
      )}
    </div>
  );
};

export default AudioProcessor;
