import React, { useEffect, useState, useCallback } from 'react';
import { Card, Row, Col, Statistic, List, Tag, Button, Space, Typography, Spin, Select, Input, Drawer, Descriptions } from 'antd';
import { audioAPI } from '../services/api';

const statusColor = (s) => ({
  PENDING: 'default',
  ANALYZING: 'processing',
  INVERTING: 'processing',
  RENDERING: 'processing',
  COMPLETED: 'success',
  FAILED: 'error',
}[s] || 'default');

export default function JobsPanel() {
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  // filters
  const [status, setStatus] = useState(undefined);
  const [userId, setUserId] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // detail drawer
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailJobId, setDetailJobId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const res = await audioAPI.getJobStats();
      setStats(res);
    } catch (e) {
      // ignore
    }
  }, []);

  const fetchList = useCallback(async (cur) => {
    try {
      cur ? setLoadingMore(true) : setLoading(true);
      const params = { limit: 20, cursor: cur, sort_by: sortBy, order: sortOrder };
      if (status) params.status = status;
      if (userId && userId.trim()) params.user_id = userId.trim();
      const res = await audioAPI.listJobs(params);
      setItems((prev) => cur ? [...prev, ...res.items] : res.items);
      setCursor(res.next_cursor || null);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [status, userId]);

  useEffect(() => {
    fetchStats();
    fetchList(null);
    const t = setInterval(fetchStats, 20000); // 与后端 TTL 对齐
    return () => clearInterval(t);
  }, [fetchStats, fetchList]);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="任务统计">
        {stats ? (
          <Row gutter={16}>
            {['PENDING','ANALYZING','INVERTING','RENDERING','COMPLETED','FAILED'].map((k) => (
              <Col key={k} xs={12} sm={8} md={4} style={{ cursor: 'pointer' }}
                   onClick={() => { setStatus(k); setCursor(null); fetchList(null); }}>
                <Statistic title={k} value={stats[k] || 0} />
              </Col>
            ))}
          </Row>
        ) : (
          <Spin />
        )}
      </Card>

      <Card title="任务列表" extra={
        <Space>
          <Select
            allowClear
            placeholder="状态"
            style={{ width: 160 }}
            value={status}
            onChange={setStatus}
            options={[
              { value: 'PENDING', label: 'PENDING' },
              { value: 'ANALYZING', label: 'ANALYZING' },
              { value: 'INVERTING', label: 'INVERTING' },
              { value: 'RENDERING', label: 'RENDERING' },
              { value: 'COMPLETED', label: 'COMPLETED' },
              { value: 'FAILED', label: 'FAILED' },
            ]}
          />
          <Input
            placeholder="User ID (可选)"
            style={{ width: 240 }}
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            allowClear
          />
          <Select
            value={sortBy}
            onChange={(v) => { setSortBy(v); setCursor(null); fetchList(null); }}
            style={{ width: 150 }}
            options={[
              { value: 'created_at', label: '按创建时间' },
              { value: 'updated_at', label: '按更新时间' },
            ]}
          />
          <Select
            value={sortOrder}
            onChange={(v) => { setSortOrder(v); setCursor(null); fetchList(null); }}
            style={{ width: 120 }}
            options={[
              { value: 'desc', label: '倒序' },
              { value: 'asc', label: '正序' },
            ]}
          />
          <Button type="primary" onClick={() => { setCursor(null); fetchList(null); }}>查询</Button>
          <Button onClick={() => { setStatus(undefined); setUserId(''); setSortBy('created_at'); setSortOrder('desc'); setCursor(null); fetchList(null); }}>重置</Button>
        </Space>
      }>
        <List
          loading={loading}
          dataSource={items}
          renderItem={(item) => (
            <List.Item
              actions={[
                <Button key="detail" size="small" onClick={async () => {
                  setDetailOpen(true);
                  setDetailJobId(item.id);
                  setDetailLoading(true);
                  try {
                    const d = await audioAPI.getJobStatus(item.id);
                    setDetailData(d);
                  } finally {
                    setDetailLoading(false);
                  }
                }}>详情</Button>,
                ...(item.status === 'FAILED' ? [
                  <Button key="retry" size="small" type="primary" danger onClick={async () => {
                    try {
                      await audioAPI.retryJob(item.id);
                      setCursor(null);
                      await fetchList(null);
                      await fetchStats();
                    } catch (e) {}
                  }}>重试</Button>
                ] : [])
              ]}
            >
              <List.Item.Meta
                title={<Space>
                  <span>{item.id}</span>
                  <Tag color={statusColor(item.status)}>{item.status}</Tag>
                </Space>}
                description={
                  <Space direction="vertical">
                    <Typography.Text type="secondary">User: {item.user_id}</Typography.Text>
                    <Typography.Text type="secondary">Mode: {item.mode} · Progress: {item.progress}%</Typography.Text>
                    <Typography.Text type="secondary">Created: {new Date(item.created_at).toLocaleString()}</Typography.Text>
                  </Space>
                }
              />
              {item.result_key && <Typography.Text copyable>{item.result_key}</Typography.Text>}
            </List.Item>
          )}
        />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button onClick={() => fetchList(cursor)} disabled={!cursor} loading={loadingMore}>
            {cursor ? '加载更多' : '没有更多'}
          </Button>
        </div>
        <Drawer
          title={`任务详情 ${detailJobId || ''}`}
          width={520}
          onClose={() => { setDetailOpen(false); setDetailJobId(null); setDetailData(null); }}
          open={detailOpen}
        >
          {detailLoading ? <Spin /> : (
            detailData ? (
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="status">{detailData.status}</Descriptions.Item>
                <Descriptions.Item label="progress">{detailData.progress}%</Descriptions.Item>
                <Descriptions.Item label="mode">{detailData.mode}</Descriptions.Item>
                <Descriptions.Item label="created_at">{detailData.created_at ? new Date(detailData.created_at).toLocaleString() : '-'}</Descriptions.Item>
                <Descriptions.Item label="updated_at">{detailData.updated_at ? new Date(detailData.updated_at).toLocaleString() : '-'}</Descriptions.Item>
                <Descriptions.Item label="error">{detailData.error || '-'}</Descriptions.Item>
                <Descriptions.Item label="download_url">
                  {detailData.download_url ? (
                    <Typography.Link href={detailData.download_url} target="_blank" copyable>
                      {detailData.download_url}
                    </Typography.Link>
                  ) : '-' }
                </Descriptions.Item>
                <Descriptions.Item label="durations (s)">
                  {detailData.metrics ? (
                    <Space size={16}>
                      <span>analyze: {detailData.metrics.analyze_s ?? '-'}</span>
                      <span>invert: {detailData.metrics.invert_s ?? '-'}</span>
                      <span>render: {detailData.metrics.render_s ?? '-'}</span>
                      <span>total: {detailData.metrics.total_s ?? '-'}</span>
                    </Space>
                  ) : '-' }
                </Descriptions.Item>
              </Descriptions>
            ) : <Typography.Text type="secondary">无详情</Typography.Text>
          )}
        </Drawer>
      </Card>
    </Space>
  );
}

