import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Card, Typography, Button, Space, Progress, message } from 'antd';
import { 
  InboxOutlined, DeleteOutlined, SoundOutlined, 
  CheckCircleOutlined 
} from '@ant-design/icons';

const { Text, Title } = Typography;

const FileUploader = ({ 
  onFileSelect, 
  accept = 'audio/*', 
  title = '上传音频文件',
  description = '支持 WAV、MP3、FLAC 等格式',
  file = null,
  maxSize = 100 * 1024 * 1024 // 100MB
}) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    
    const selectedFile = acceptedFiles[0];
    
    // 检查文件大小
    if (selectedFile.size > maxSize) {
      message.error(`文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`);
      return;
    }

    // 检查文件类型
    if (!selectedFile.type.startsWith('audio/')) {
      message.error('请选择音频文件');
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);

      // 模拟上传进度
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // 调用上传回调
      await onFileSelect(selectedFile);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
      }, 500);
      
    } catch (error) {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [onFileSelect, maxSize]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.wav', '.mp3', '.flac', '.aac', '.ogg', '.m4a']
    },
    multiple: false,
    disabled: uploading
  });

  const handleRemoveFile = (e) => {
    e.stopPropagation();
    onFileSelect(null);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (file) => {
    // 这里可以添加音频时长检测逻辑
    return '未知';
  };

  if (file && !uploading) {
    // 显示已上传的文件
    return (
      <Card className="file-uploaded">
        <Space direction="vertical" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Space>
              <CheckCircleOutlined style={{ color: '#52c41a', fontSize: '20px' }} />
              <div>
                <Title level={5} style={{ margin: 0 }}>
                  {file.name}
                </Title>
                <Text type="secondary">
                  {formatFileSize(file.file?.size || 0)} • 时长: {formatDuration(file.file)}
                </Text>
              </div>
            </Space>
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />}
              onClick={handleRemoveFile}
            >
              移除
            </Button>
          </div>
        </Space>
      </Card>
    );
  }

  return (
    <div>
      <div
        {...getRootProps()}
        className={`upload-area ${isDragActive ? 'dragover' : ''} ${uploading ? 'uploading' : ''}`}
        style={{
          opacity: uploading ? 0.7 : 1,
          pointerEvents: uploading ? 'none' : 'auto'
        }}
      >
        <input {...getInputProps()} />
        
        {uploading ? (
          <Space direction="vertical" align="center">
            <SoundOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            <Title level={4} style={{ margin: '16px 0 8px' }}>
              上传中...
            </Title>
            <Progress 
              percent={uploadProgress} 
              style={{ width: '200px' }}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </Space>
        ) : (
          <Space direction="vertical" align="center">
            <InboxOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
            <Title level={4} style={{ margin: '16px 0 8px' }}>
              {isDragActive ? '释放文件以上传' : title}
            </Title>
            <Text type="secondary" style={{ marginBottom: '16px' }}>
              {description}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              拖拽文件到此处，或点击选择文件
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              最大文件大小: {Math.round(maxSize / 1024 / 1024)}MB
            </Text>
          </Space>
        )}
      </div>
    </div>
  );
};

export default FileUploader;
