import React, { useEffect, useRef } from 'react';
import { Card, Row, Col, Statistic, Typography, Space } from 'antd';
import { SoundOutlined, BarChartOutlined, ThunderboltOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { Title, Text } = Typography;

const VisualizationPanel = ({ jobStatus, style }) => {
  const chartRef = useRef(null);

  // 生成频谱图数据
  const getSpectrumData = () => {
    if (!jobStatus?.metrics) return [];
    
    // 模拟频谱数据
    const frequencies = [];
    const magnitudes = [];
    
    for (let i = 0; i < 50; i++) {
      const freq = 20 * Math.pow(2, i / 8); // 对数频率分布
      if (freq > 20000) break;
      
      frequencies.push(freq);
      magnitudes.push(-20 + Math.random() * 40); // 模拟幅度
    }
    
    return frequencies.map((freq, index) => [freq, magnitudes[index]]);
  };

  // EQ 曲线图配置
  const getEQChartOption = () => {
    const eqParams = jobStatus?.style_params?.eq || [];
    
    // 生成频率响应曲线
    const frequencies = [];
    const responses = [];
    
    for (let i = 0; i < 200; i++) {
      const freq = 20 * Math.pow(1000, i / 199); // 20Hz 到 20kHz
      frequencies.push(freq);
      
      let totalGain = 0;
      eqParams.forEach(eq => {
        if (eq.type === 'peaking') {
          const ratio = freq / eq.f_hz;
          const gain = eq.gain_db / (1 + eq.q * Math.pow(ratio - 1/ratio, 2));
          totalGain += gain;
        }
      });
      
      responses.push(totalGain);
    }
    
    return {
      title: {
        text: 'EQ 频率响应',
        left: 'center',
        textStyle: { fontSize: 14 }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const freq = params[0].data[0];
          const gain = params[0].data[1];
          return `频率: ${freq < 1000 ? freq.toFixed(0) + 'Hz' : (freq/1000).toFixed(1) + 'kHz'}<br/>增益: ${gain.toFixed(1)}dB`;
        }
      },
      xAxis: {
        type: 'log',
        name: '频率 (Hz)',
        nameLocation: 'middle',
        nameGap: 30,
        min: 20,
        max: 20000,
        axisLabel: {
          formatter: (value) => {
            if (value >= 1000) return (value / 1000) + 'k';
            return value;
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '增益 (dB)',
        nameLocation: 'middle',
        nameGap: 40
      },
      series: [{
        data: frequencies.map((freq, index) => [freq, responses[index]]),
        type: 'line',
        smooth: true,
        lineStyle: { color: '#1890ff', width: 2 },
        areaStyle: { 
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
              { offset: 1, color: 'rgba(24, 144, 255, 0.1)' }
            ]
          }
        }
      }],
      grid: {
        left: '10%',
        right: '5%',
        bottom: '15%',
        top: '15%'
      }
    };
  };

  // 频谱对比图配置
  const getSpectrumChartOption = () => {
    const spectrumData = getSpectrumData();
    
    return {
      title: {
        text: '频谱对比',
        left: 'center',
        textStyle: { fontSize: 14 }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const freq = params[0].data[0];
          const mag = params[0].data[1];
          return `频率: ${freq < 1000 ? freq.toFixed(0) + 'Hz' : (freq/1000).toFixed(1) + 'kHz'}<br/>幅度: ${mag.toFixed(1)}dB`;
        }
      },
      legend: {
        data: ['原始', '处理后'],
        bottom: 0
      },
      xAxis: {
        type: 'log',
        name: '频率 (Hz)',
        nameLocation: 'middle',
        nameGap: 30,
        min: 20,
        max: 20000,
        axisLabel: {
          formatter: (value) => {
            if (value >= 1000) return (value / 1000) + 'k';
            return value;
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '幅度 (dB)',
        nameLocation: 'middle',
        nameGap: 40
      },
      series: [
        {
          name: '原始',
          data: spectrumData,
          type: 'line',
          smooth: true,
          lineStyle: { color: '#ff4d4f', width: 2 }
        },
        {
          name: '处理后',
          data: spectrumData.map(([freq, mag]) => [freq, mag + Math.random() * 4 - 2]),
          type: 'line',
          smooth: true,
          lineStyle: { color: '#52c41a', width: 2 }
        }
      ],
      grid: {
        left: '10%',
        right: '5%',
        bottom: '20%',
        top: '15%'
      }
    };
  };

  // 动态范围图配置
  const getDynamicsChartOption = () => {
    // 模拟动态范围数据
    const timeData = [];
    const originalData = [];
    const processedData = [];
    
    for (let i = 0; i < 100; i++) {
      timeData.push(i / 10); // 10秒时间轴
      originalData.push(-10 + Math.random() * 20);
      processedData.push(-8 + Math.random() * 16);
    }
    
    return {
      title: {
        text: '动态范围对比',
        left: 'center',
        textStyle: { fontSize: 14 }
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const time = params[0].axisValue;
          return `时间: ${time}s<br/>${params.map(p => `${p.seriesName}: ${p.data.toFixed(1)}dB`).join('<br/>')}`;
        }
      },
      legend: {
        data: ['原始', '处理后'],
        bottom: 0
      },
      xAxis: {
        type: 'category',
        data: timeData,
        name: '时间 (s)',
        nameLocation: 'middle',
        nameGap: 30
      },
      yAxis: {
        type: 'value',
        name: '电平 (dB)',
        nameLocation: 'middle',
        nameGap: 40
      },
      series: [
        {
          name: '原始',
          data: originalData,
          type: 'line',
          smooth: true,
          lineStyle: { color: '#ff4d4f', width: 1 },
          symbol: 'none'
        },
        {
          name: '处理后',
          data: processedData,
          type: 'line',
          smooth: true,
          lineStyle: { color: '#52c41a', width: 1 },
          symbol: 'none'
        }
      ],
      grid: {
        left: '10%',
        right: '5%',
        bottom: '20%',
        top: '15%'
      }
    };
  };

  if (!jobStatus) {
    return null;
  }

  const metrics = jobStatus.metrics || {};
  const styleParams = jobStatus.style_params || {};

  return (
    <Card title="可视化分析" style={style}>
      {/* 关键指标 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Statistic
            title="LUFS 响度"
            value={styleParams.lufs?.target_lufs || -23}
            precision={1}
            suffix="LU"
            prefix={<SoundOutlined />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="真峰值"
            value={styleParams.limiter?.tp_db || -1.0}
            precision={1}
            suffix="dB"
            prefix={<ThunderboltOutlined />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="EQ 段数"
            value={styleParams.eq?.length || 0}
            prefix={<BarChartOutlined />}
          />
        </Col>
        <Col xs={12} sm={6}>
          <Statistic
            title="处理质量"
            value={((1 - (metrics.artifacts_rate || 0)) * 100)}
            precision={1}
            suffix="%"
          />
        </Col>
      </Row>

      {/* 图表展示 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <ReactECharts 
            option={getEQChartOption()} 
            style={{ height: '300px' }}
            opts={{ renderer: 'svg' }}
          />
        </Col>
        <Col xs={24} lg={12}>
          <ReactECharts 
            option={getSpectrumChartOption()} 
            style={{ height: '300px' }}
            opts={{ renderer: 'svg' }}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <ReactECharts 
            option={getDynamicsChartOption()} 
            style={{ height: '250px' }}
            opts={{ renderer: 'svg' }}
          />
        </Col>
      </Row>

      {/* 处理信息 */}
      <div style={{ marginTop: 24, padding: 16, background: '#fafafa', borderRadius: 8 }}>
        <Title level={5}>处理信息</Title>
        <Space direction="vertical">
          <Text>
            <strong>处理模式:</strong> {styleParams.metadata?.mode || 'A'} 模式
          </Text>
          <Text>
            <strong>置信度:</strong> {((styleParams.metadata?.confidence || 0.5) * 100).toFixed(0)}%
          </Text>
          <Text>
            <strong>STFT 距离:</strong> {(metrics.stft_dist || 0).toFixed(3)}
          </Text>
          <Text>
            <strong>Mel 距离:</strong> {(metrics.mel_dist || 0).toFixed(3)}
          </Text>
          <Text>
            <strong>LUFS 误差:</strong> {(metrics.lufs_err || 0).toFixed(1)} LU
          </Text>
        </Space>
      </div>
    </Card>
  );
};

export default VisualizationPanel;
