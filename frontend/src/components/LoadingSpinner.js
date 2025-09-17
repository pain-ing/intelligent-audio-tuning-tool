import React from 'react';
import { Spin, Typography } from 'antd';
import { SoundOutlined } from '@ant-design/icons';

const { Text } = Typography;

const LoadingSpinner = ({ 
  size = 'large', 
  tip = '加载中...', 
  style = {},
  showIcon = true 
}) => {
  return (
    <div 
      style={{ 
        textAlign: 'center', 
        padding: '50px 20px',
        ...style 
      }}
    >
      <Spin 
        size={size} 
        tip={tip}
        indicator={showIcon ? <SoundOutlined spin style={{ fontSize: 24, color: '#3CE6BE' }} /> : undefined}
      />
      {tip && (
        <div style={{ marginTop: 16 }}>
          <Text style={{ color: '#B4FFF0', fontSize: '14px' }}>
            {tip}
          </Text>
        </div>
      )}
    </div>
  );
};

export default LoadingSpinner;
