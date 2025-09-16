import React, { useState, useEffect } from 'react';
import { 
  Card, Row, Col, Slider, InputNumber, Switch, Button,
  Collapse, Space, Typography, message
} from 'antd';
import { 
  SettingOutlined, SoundOutlined, ThunderboltOutlined,
  AudioOutlined, CompressOutlined, ReloadOutlined
} from '@ant-design/icons';

const { Panel } = Collapse;
const { Text } = Typography;

const ParameterEditor = ({ parameters, onParametersChange, style }) => {
  const [params, setParams] = useState(parameters || {});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setParams(parameters || {});
    setHasChanges(false);
  }, [parameters]);

  const updateParameter = (section, key, value) => {
    const newParams = {
      ...params,
      [section]: {
        ...params[section],
        [key]: value
      }
    };
    setParams(newParams);
    setHasChanges(true);
  };

  const updateEQBand = (index, key, value) => {
    const newEQ = [...(params.eq || [])];
    newEQ[index] = {
      ...newEQ[index],
      [key]: value
    };
    setParams({
      ...params,
      eq: newEQ
    });
    setHasChanges(true);
  };

  const addEQBand = () => {
    const newEQ = [...(params.eq || []), {
      type: 'peaking',
      f_hz: 1000,
      gain_db: 0,
      q: 1.0
    }];
    setParams({
      ...params,
      eq: newEQ
    });
    setHasChanges(true);
  };

  const removeEQBand = (index) => {
    const newEQ = (params.eq || []).filter((_, i) => i !== index);
    setParams({
      ...params,
      eq: newEQ
    });
    setHasChanges(true);
  };

  const handleApplyChanges = () => {
    onParametersChange(params);
    setHasChanges(false);
    message.success('参数已应用');
  };

  const handleResetChanges = () => {
    setParams(parameters || {});
    setHasChanges(false);
    message.info('参数已重置');
  };

  const formatFrequency = (freq) => {
    if (freq >= 1000) {
      return `${(freq / 1000).toFixed(1)}kHz`;
    }
    return `${freq}Hz`;
  };

  return (
    <Card 
      title={
        <Space>
          <SettingOutlined />
          参数编辑器
        </Space>
      }
      extra={
        hasChanges && (
          <Space>
            <Button size="small" onClick={handleResetChanges}>
              <ReloadOutlined /> 重置
            </Button>
            <Button type="primary" size="small" onClick={handleApplyChanges}>
              应用更改
            </Button>
          </Space>
        )
      }
      style={style}
    >
      <Collapse defaultActiveKey={['eq', 'lufs']} ghost>
        {/* EQ 参数 */}
        <Panel 
          header={
            <Space>
              <AudioOutlined />
              均衡器 ({(params.eq || []).length} 段)
            </Space>
          } 
          key="eq"
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            {(params.eq || []).map((band, index) => (
              <Card 
                key={index} 
                size="small" 
                title={`EQ ${index + 1}`}
                extra={
                  <Button 
                    type="text" 
                    danger 
                    size="small"
                    onClick={() => removeEQBand(index)}
                  >
                    删除
                  </Button>
                }
              >
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={8}>
                    <Text strong>频率</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Slider
                        min={20}
                        max={20000}
                        value={band.f_hz}
                        onChange={(value) => updateEQBand(index, 'f_hz', value)}
                        style={{ flex: 1 }}
                        tooltip={{
                          formatter: formatFrequency
                        }}
                      />
                      <InputNumber
                        size="small"
                        value={band.f_hz}
                        onChange={(value) => updateEQBand(index, 'f_hz', value)}
                        min={20}
                        max={20000}
                        style={{ width: 80 }}
                        formatter={(value) => formatFrequency(value)}
                        parser={(value) => value.replace(/[^\d]/g, '')}
                      />
                    </div>
                  </Col>
                  
                  <Col xs={24} sm={8}>
                    <Text strong>增益 (dB)</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Slider
                        min={-20}
                        max={20}
                        step={0.1}
                        value={band.gain_db}
                        onChange={(value) => updateEQBand(index, 'gain_db', value)}
                        style={{ flex: 1 }}
                      />
                      <InputNumber
                        size="small"
                        value={band.gain_db}
                        onChange={(value) => updateEQBand(index, 'gain_db', value)}
                        min={-20}
                        max={20}
                        step={0.1}
                        style={{ width: 80 }}
                      />
                    </div>
                  </Col>
                  
                  <Col xs={24} sm={8}>
                    <Text strong>Q 值</Text>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Slider
                        min={0.1}
                        max={10}
                        step={0.1}
                        value={band.q}
                        onChange={(value) => updateEQBand(index, 'q', value)}
                        style={{ flex: 1 }}
                      />
                      <InputNumber
                        size="small"
                        value={band.q}
                        onChange={(value) => updateEQBand(index, 'q', value)}
                        min={0.1}
                        max={10}
                        step={0.1}
                        style={{ width: 80 }}
                      />
                    </div>
                  </Col>
                </Row>
              </Card>
            ))}
            
            <Button type="dashed" onClick={addEQBand} style={{ width: '100%' }}>
              + 添加 EQ 段
            </Button>
          </Space>
        </Panel>

        {/* LUFS 参数 */}
        <Panel 
          header={
            <Space>
              <SoundOutlined />
              响度归一化
            </Space>
          } 
          key="lufs"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12}>
              <Text strong>目标 LUFS</Text>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Slider
                  min={-40}
                  max={-6}
                  step={0.1}
                  value={params.lufs?.target_lufs || -23}
                  onChange={(value) => updateParameter('lufs', 'target_lufs', value)}
                  style={{ flex: 1 }}
                />
                <InputNumber
                  size="small"
                  value={params.lufs?.target_lufs || -23}
                  onChange={(value) => updateParameter('lufs', 'target_lufs', value)}
                  min={-40}
                  max={-6}
                  step={0.1}
                  style={{ width: 80 }}
                  suffix="LU"
                />
              </div>
            </Col>
          </Row>
        </Panel>

        {/* 压缩参数 */}
        <Panel 
          header={
            <Space>
              <CompressOutlined />
              动态压缩
            </Space>
          } 
          key="compression"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24}>
              <Space>
                <Text strong>启用压缩</Text>
                <Switch
                  checked={params.compression?.enabled || false}
                  onChange={(checked) => updateParameter('compression', 'enabled', checked)}
                />
              </Space>
            </Col>
            
            {params.compression?.enabled && (
              <>
                <Col xs={24} sm={12}>
                  <Text strong>阈值 (dB)</Text>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Slider
                      min={-40}
                      max={0}
                      value={params.compression?.threshold_db || -20}
                      onChange={(value) => updateParameter('compression', 'threshold_db', value)}
                      style={{ flex: 1 }}
                    />
                    <InputNumber
                      size="small"
                      value={params.compression?.threshold_db || -20}
                      onChange={(value) => updateParameter('compression', 'threshold_db', value)}
                      min={-40}
                      max={0}
                      style={{ width: 80 }}
                    />
                  </div>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Text strong>压缩比</Text>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Slider
                      min={1}
                      max={20}
                      step={0.1}
                      value={params.compression?.ratio || 2}
                      onChange={(value) => updateParameter('compression', 'ratio', value)}
                      style={{ flex: 1 }}
                    />
                    <InputNumber
                      size="small"
                      value={params.compression?.ratio || 2}
                      onChange={(value) => updateParameter('compression', 'ratio', value)}
                      min={1}
                      max={20}
                      step={0.1}
                      style={{ width: 80 }}
                      suffix=":1"
                    />
                  </div>
                </Col>
              </>
            )}
          </Row>
        </Panel>

        {/* 限制器参数 */}
        <Panel 
          header={
            <Space>
              <ThunderboltOutlined />
              限制器
            </Space>
          } 
          key="limiter"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12}>
              <Text strong>真峰值限制 (dB)</Text>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Slider
                  min={-6}
                  max={0}
                  step={0.1}
                  value={params.limiter?.tp_db || -1}
                  onChange={(value) => updateParameter('limiter', 'tp_db', value)}
                  style={{ flex: 1 }}
                />
                <InputNumber
                  size="small"
                  value={params.limiter?.tp_db || -1}
                  onChange={(value) => updateParameter('limiter', 'tp_db', value)}
                  min={-6}
                  max={0}
                  step={0.1}
                  style={{ width: 80 }}
                />
              </div>
            </Col>
            
            <Col xs={24} sm={12}>
              <Text strong>释放时间 (ms)</Text>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Slider
                  min={10}
                  max={1000}
                  value={params.limiter?.release_ms || 100}
                  onChange={(value) => updateParameter('limiter', 'release_ms', value)}
                  style={{ flex: 1 }}
                />
                <InputNumber
                  size="small"
                  value={params.limiter?.release_ms || 100}
                  onChange={(value) => updateParameter('limiter', 'release_ms', value)}
                  min={10}
                  max={1000}
                  style={{ width: 80 }}
                />
              </div>
            </Col>
          </Row>
        </Panel>

        {/* 立体声参数 */}
        <Panel 
          header={
            <Space>
              <AudioOutlined />
              立体声处理
            </Space>
          } 
          key="stereo"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12}>
              <Text strong>立体声宽度</Text>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Slider
                  min={0}
                  max={2}
                  step={0.01}
                  value={params.stereo?.width || 1}
                  onChange={(value) => updateParameter('stereo', 'width', value)}
                  style={{ flex: 1 }}
                />
                <InputNumber
                  size="small"
                  value={params.stereo?.width || 1}
                  onChange={(value) => updateParameter('stereo', 'width', value)}
                  min={0}
                  max={2}
                  step={0.01}
                  style={{ width: 80 }}
                />
              </div>
            </Col>
          </Row>
        </Panel>

        {/* 音高参数 */}
        <Panel 
          header={
            <Space>
              <AudioOutlined />
              音高调整
            </Space>
          } 
          key="pitch"
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12}>
              <Text strong>音高偏移 (半音)</Text>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Slider
                  min={-12}
                  max={12}
                  step={0.01}
                  value={params.pitch?.semitones || 0}
                  onChange={(value) => updateParameter('pitch', 'semitones', value)}
                  style={{ flex: 1 }}
                />
                <InputNumber
                  size="small"
                  value={params.pitch?.semitones || 0}
                  onChange={(value) => updateParameter('pitch', 'semitones', value)}
                  min={-12}
                  max={12}
                  step={0.01}
                  style={{ width: 80 }}
                />
              </div>
            </Col>
          </Row>
        </Panel>
      </Collapse>

      {hasChanges && (
        <div style={{ 
          marginTop: 16, 
          padding: 12, 
          background: '#fff7e6', 
          border: '1px solid #ffd591',
          borderRadius: 6 
        }}>
          <Text type="warning">
            参数已修改，点击"应用更改"以重新处理音频
          </Text>
        </div>
      )}
    </Card>
  );
};

export default ParameterEditor;
