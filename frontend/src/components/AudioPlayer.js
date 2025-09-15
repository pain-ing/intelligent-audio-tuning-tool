import React, { useState, useRef, useEffect } from 'react';
import { Card, Button, Slider, Space, Typography } from 'antd';
import { 
  PlayCircleOutlined, PauseCircleOutlined, SoundOutlined,
  StepBackwardOutlined, StepForwardOutlined
} from '@ant-design/icons';

const { Text } = Typography;

const AudioPlayer = ({ file, url, title = '音频播放器' }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [audioUrl, setAudioUrl] = useState(null);
  const audioRef = useRef(null);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setAudioUrl(url);
      return () => URL.revokeObjectURL(url);
    } else if (url) {
      setAudioUrl(url);
    }
  }, [file, url]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioUrl]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (value) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newTime = (value / 100) * duration;
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (value) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newVolume = value / 100;
    audio.volume = newVolume;
    setVolume(newVolume);
  };

  const skipBackward = () => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = Math.max(0, audio.currentTime - 10);
  };

  const skipForward = () => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.currentTime = Math.min(duration, audio.currentTime + 10);
  };

  const formatTime = (time) => {
    if (isNaN(time)) return '0:00';
    
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  if (!audioUrl) {
    return (
      <Card className="audio-player disabled">
        <Space>
          <SoundOutlined style={{ color: '#d9d9d9' }} />
          <Text type="secondary">暂无音频</Text>
        </Space>
      </Card>
    );
  }

  return (
    <Card className="audio-player" title={title}>
      <audio ref={audioRef} src={audioUrl} preload="metadata" />
      
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* 播放控制 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Button
            type="text"
            icon={<StepBackwardOutlined />}
            onClick={skipBackward}
            title="后退 10 秒"
          />
          
          <Button
            type="primary"
            shape="circle"
            size="large"
            icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={togglePlay}
          />
          
          <Button
            type="text"
            icon={<StepForwardOutlined />}
            onClick={skipForward}
            title="前进 10 秒"
          />
          
          <div style={{ flex: 1, marginLeft: '16px' }}>
            <Slider
              value={duration > 0 ? (currentTime / duration) * 100 : 0}
              onChange={handleSeek}
              tooltip={{
                formatter: (value) => formatTime((value / 100) * duration)
              }}
            />
          </div>
          
          <Text style={{ minWidth: '80px', textAlign: 'center' }}>
            {formatTime(currentTime)} / {formatTime(duration)}
          </Text>
        </div>

        {/* 音量控制 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <SoundOutlined />
          <Slider
            style={{ flex: 1, maxWidth: '150px' }}
            value={volume * 100}
            onChange={handleVolumeChange}
            tooltip={{
              formatter: (value) => `${Math.round(value)}%`
            }}
          />
        </div>
      </Space>
    </Card>
  );
};

export default AudioPlayer;
