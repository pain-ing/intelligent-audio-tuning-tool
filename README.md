# 智能音频调音工具 (Audio Style Matching Tool)

基于参考音频自动调音的智能工具，支持任意时长音频处理。

## 快速开始

### 1. 环境准备
```bash
# 复制环境配置
cp .env.example .env

# 一键启动（构建镜像 + 启动服务 + 数据库迁移）
make setup
```

### 2. 验证服务
```bash
# 检查服务状态
make logs

# 测试 API
curl http://localhost:8080/health
```

### 3. 使用示例
```bash
# 1. 获取上传签名
curl -X POST "http://localhost:8080/uploads/sign" \
  -H "Content-Type: application/json" \
  -d '{"content_type": "audio/wav", "ext": ".wav"}'

# 2. 创建处理任务
curl -X POST "http://localhost:8080/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "A",
    "ref_key": "uploads/reference.wav",
    "tgt_key": "uploads/target.wav"
  }'

# 3. 查询任务状态
curl "http://localhost:8080/jobs/{job_id}"
```

## 服务架构

- **API (Port 8080)**: FastAPI 后端服务
- **Worker**: Celery 音频处理工作进程
- **Redis (Port 6379)**: 任务队列
- **PostgreSQL (Port 5432)**: 数据存储
- **MinIO (Port 9000/9001)**: 对象存储

## 开发命令

```bash
make help          # 查看所有命令
make build         # 构建镜像
make up            # 启动服务
make down          # 停止服务
make logs          # 查看日志
make migrate       # 运行数据库迁移
make shell-api     # 进入 API 容器
make shell-worker  # 进入 Worker 容器
```

## 项目结构

```
├── api/                 # FastAPI 后端服务
│   ├── app/
│   │   ├── main.py     # API 路由
│   │   ├── models.py   # 数据模型
│   │   └── database.py # 数据库配置
│   ├── alembic/        # 数据库迁移
│   └── requirements.txt
├── worker/             # Celery 工作进程
│   ├── app/
│   │   └── worker.py   # 音频处理任务
│   └── requirements.txt
├── deploy/
│   └── docker-compose.yml
├── 产品需求文档.md
├── 技术架构文档.md
├── 实施指南文档.md
└── 项目总结文档.md
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy + Alembic
- **任务队列**: Celery + Redis
- **数据库**: PostgreSQL
- **对象存储**: MinIO (S3 兼容)
- **音频处理**: librosa + pyloudnorm + scipy
- **容器化**: Docker + Docker Compose

## 下一步开发

1. 实现真实的音频分析算法 (analyze_features)
2. 实现参数反演算法 (invert_params)  
3. 实现音频渲染引擎 (render_audio)
4. 接入对象存储签名上传
5. 添加前端界面
6. 性能优化与监控

详细技术方案请参考项目文档。
