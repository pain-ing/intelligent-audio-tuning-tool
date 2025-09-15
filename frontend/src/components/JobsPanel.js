import React, { useEffect, useState, useCallback } from 'react';
import { Card, Row, Col, Statistic, List, Tag, Button, Space, Typography, Spin } from 'antd';
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
      const res = await audioAPI.listJobs({ limit: 20, cursor: cur });
      setItems((prev) => cur ? [...prev, ...res.items] : res.items);
      setCursor(res.next_cursor || null);
    } catch (e) {
      // ignore
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

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
              <Col key={k} xs={12} sm={8} md={4}>
                <Statistic title={k} value={stats[k] || 0} />
              </Col>
            ))}
          </Row>
        ) : (
          <Spin />
        )}
      </Card>

      <Card title="任务列表">
        <List
          loading={loading}
          dataSource={items}
          renderItem={(item) => (
            <List.Item>
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
      </Card>
    </Space>
  );
}

