import React, { useState } from 'react';
import { Layout, Typography, Tabs } from 'antd';
import { SoundOutlined } from '@ant-design/icons';
import AudioProcessor from './components/AudioProcessor';
import PresetManager from './components/PresetManager';
import JobsPanel from './components/JobsPanel';
import './App.css';

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
              <AudioProcessor />
            </TabPane>
            <TabPane tab="预设管理" key="presets">
              <PresetManager />
            </TabPane>
            <TabPane tab="任务列表" key="jobs">
              <React.Suspense fallback={null}>
                <JobsPanel />
              </React.Suspense>
            </TabPane>
          </Tabs>
        </div>
      </Content>
    </Layout>
  );
}

export default App;
