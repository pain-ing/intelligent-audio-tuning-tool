import React, { useState, Suspense, lazy } from 'react';
import { Layout, Typography, Tabs, Spin } from 'antd';
import { SoundOutlined } from '@ant-design/icons';
import './App.css';

// 懒加载组件以减少初始包大小
const AudioProcessor = lazy(() => import('./components/AudioProcessor'));
const PresetManager = lazy(() => import('./components/PresetManager'));
const JobsPanel = lazy(() => import('./components/JobsPanel'));

const { Header, Content } = Layout;
const { Title } = Typography;
const { TabPane } = Tabs;

function App() {
  const [activeTab, setActiveTab] = useState('processor');

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <div className="logo">
            <SoundOutlined style={{ fontSize: '24px', marginRight: '12px' }} />
            <Title level={3} style={{ margin: 0, color: 'white' }}>
              智能音频调音工具
            </Title>
          </div>
          <div className="header-subtitle">
            基于参考音频的智能调音匹配
          </div>
        </div>
      </Header>
      
      <Content className="app-content">
        <div className="content-container">
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            size="large"
            className="main-tabs"
          >
            <TabPane tab="音频处理" key="processor">
              <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载中..." /></div>}>
                <AudioProcessor />
              </Suspense>
            </TabPane>
            <TabPane tab="预设管理" key="presets">
              <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载中..." /></div>}>
                <PresetManager />
              </Suspense>
            </TabPane>
            <TabPane tab="任务列表" key="jobs">
              <Suspense fallback={<div style={{ textAlign: 'center', padding: '50px' }}><Spin size="large" tip="加载中..." /></div>}>
                <JobsPanel />
              </Suspense>
            </TabPane>
          </Tabs>
        </div>
      </Content>
    </Layout>
  );
}

export default App;
