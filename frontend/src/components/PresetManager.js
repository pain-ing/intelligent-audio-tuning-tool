import React, { useState, useEffect } from 'react';
import { 
  Card, List, Button, Modal, Form, Input, Select, Space, 
  Typography, message, Popconfirm, Tag, Row, Col 
} from 'antd';
import { 
  PlusOutlined, EditOutlined, DeleteOutlined, 
  SaveOutlined, StarOutlined, StarFilled 
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

const PresetManager = () => {
  const [presets, setPresets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingPreset, setEditingPreset] = useState(null);
  const [form] = Form.useForm();

  // 模拟预设数据
  const mockPresets = [
    {
      id: '1',
      name: '人声增强',
      description: '增强人声清晰度，适用于播客和语音录制',
      category: 'vocal',
      is_favorite: true,
      parameters: {
        eq: [
          { type: 'peaking', f_hz: 2000, gain_db: 3, q: 1.5 },
          { type: 'peaking', f_hz: 5000, gain_db: 2, q: 1.0 }
        ],
        lufs: { target_lufs: -16 },
        compression: { enabled: true, threshold_db: -18, ratio: 3 }
      },
      created_at: '2024-01-15'
    },
    {
      id: '2',
      name: '音乐母带',
      description: '适用于音乐制作的母带处理预设',
      category: 'music',
      is_favorite: false,
      parameters: {
        eq: [
          { type: 'peaking', f_hz: 100, gain_db: 1, q: 0.7 },
          { type: 'peaking', f_hz: 10000, gain_db: 1.5, q: 1.2 }
        ],
        lufs: { target_lufs: -14 },
        limiter: { tp_db: -1, release_ms: 50 }
      },
      created_at: '2024-01-10'
    },
    {
      id: '3',
      name: '广播标准',
      description: '符合广播电台标准的响度处理',
      category: 'broadcast',
      is_favorite: false,
      parameters: {
        lufs: { target_lufs: -23 },
        limiter: { tp_db: -1, release_ms: 100 },
        compression: { enabled: true, threshold_db: -20, ratio: 2.5 }
      },
      created_at: '2024-01-05'
    }
  ];

  useEffect(() => {
    loadPresets();
  }, []);

  const loadPresets = async () => {
    setLoading(true);
    try {
      // 模拟 API 调用
      setTimeout(() => {
        setPresets(mockPresets);
        setLoading(false);
      }, 500);
    } catch (error) {
      message.error('加载预设失败');
      setLoading(false);
    }
  };

  const handleCreatePreset = () => {
    setEditingPreset(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEditPreset = (preset) => {
    setEditingPreset(preset);
    form.setFieldsValue({
      name: preset.name,
      description: preset.description,
      category: preset.category
    });
    setModalVisible(true);
  };

  const handleDeletePreset = async (id) => {
    try {
      // 模拟 API 调用
      setPresets(presets.filter(p => p.id !== id));
      message.success('预设已删除');
    } catch (error) {
      message.error('删除预设失败');
    }
  };

  const handleToggleFavorite = async (id) => {
    try {
      // 模拟 API 调用
      setPresets(presets.map(p => 
        p.id === id ? { ...p, is_favorite: !p.is_favorite } : p
      ));
      message.success('收藏状态已更新');
    } catch (error) {
      message.error('更新收藏状态失败');
    }
  };

  const handleSavePreset = async (values) => {
    try {
      if (editingPreset) {
        // 编辑现有预设
        setPresets(presets.map(p => 
          p.id === editingPreset.id 
            ? { ...p, ...values, updated_at: new Date().toISOString().split('T')[0] }
            : p
        ));
        message.success('预设已更新');
      } else {
        // 创建新预设
        const newPreset = {
          id: Date.now().toString(),
          ...values,
          is_favorite: false,
          parameters: {
            eq: [],
            lufs: { target_lufs: -23 },
            limiter: { tp_db: -1, release_ms: 100 }
          },
          created_at: new Date().toISOString().split('T')[0]
        };
        setPresets([newPreset, ...presets]);
        message.success('预设已创建');
      }
      setModalVisible(false);
    } catch (error) {
      message.error('保存预设失败');
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      vocal: 'blue',
      music: 'green',
      broadcast: 'orange',
      podcast: 'purple',
      other: 'default'
    };
    return colors[category] || 'default';
  };

  const getCategoryName = (category) => {
    const names = {
      vocal: '人声',
      music: '音乐',
      broadcast: '广播',
      podcast: '播客',
      other: '其他'
    };
    return names[category] || '其他';
  };

  const renderPresetItem = (preset) => (
    <List.Item
      actions={[
        <Button
          type="text"
          icon={preset.is_favorite ? <StarFilled style={{ color: '#faad14' }} /> : <StarOutlined />}
          onClick={() => handleToggleFavorite(preset.id)}
        />,
        <Button
          type="text"
          icon={<EditOutlined />}
          onClick={() => handleEditPreset(preset)}
        />,
        <Popconfirm
          title="确定要删除这个预设吗？"
          onConfirm={() => handleDeletePreset(preset.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
          />
        </Popconfirm>
      ]}
    >
      <List.Item.Meta
        title={
          <Space>
            {preset.name}
            <Tag color={getCategoryColor(preset.category)}>
              {getCategoryName(preset.category)}
            </Tag>
          </Space>
        }
        description={
          <div>
            <Text type="secondary">{preset.description}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: '12px' }}>
              创建时间: {preset.created_at}
            </Text>
          </div>
        }
      />
    </List.Item>
  );

  return (
    <div className="preset-manager">
      <Card
        title={
          <Space>
            <SaveOutlined />
            预设管理
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreatePreset}>
            新建预设
          </Button>
        }
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
                  {presets.length}
                </Title>
                <Text type="secondary">总预设数</Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ margin: 0, color: '#faad14' }}>
                  {presets.filter(p => p.is_favorite).length}
                </Title>
                <Text type="secondary">收藏预设</Text>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small">
              <div style={{ textAlign: 'center' }}>
                <Title level={3} style={{ margin: 0, color: '#52c41a' }}>
                  {new Set(presets.map(p => p.category)).size}
                </Title>
                <Text type="secondary">预设分类</Text>
              </div>
            </Card>
          </Col>
        </Row>

        <List
          loading={loading}
          dataSource={presets}
          renderItem={renderPresetItem}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个预设`
          }}
        />
      </Card>

      <Modal
        title={editingPreset ? '编辑预设' : '新建预设'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={() => form.submit()}
        okText="保存"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSavePreset}
        >
          <Form.Item
            name="name"
            label="预设名称"
            rules={[{ required: true, message: '请输入预设名称' }]}
          >
            <Input placeholder="输入预设名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="预设描述"
            rules={[{ required: true, message: '请输入预设描述' }]}
          >
            <TextArea 
              rows={3} 
              placeholder="描述这个预设的用途和特点"
            />
          </Form.Item>

          <Form.Item
            name="category"
            label="预设分类"
            rules={[{ required: true, message: '请选择预设分类' }]}
          >
            <Select placeholder="选择预设分类">
              <Select.Option value="vocal">人声</Select.Option>
              <Select.Option value="music">音乐</Select.Option>
              <Select.Option value="broadcast">广播</Select.Option>
              <Select.Option value="podcast">播客</Select.Option>
              <Select.Option value="other">其他</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PresetManager;
