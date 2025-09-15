# 智能音频调音工具 (Audio Style Matching Tool)

[![CI](https://github.com/pain-ing/intelligent-audio-tuning-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/pain-ing/intelligent-audio-tuning-tool/actions/workflows/ci.yml)


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
  -d '{"content_type": "audio/wav", "extension": ".wav"}'

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

## 环境变量

参见 .env.example，关键变量如下：

- DATABASE_URL：数据库连接串（示例：postgresql://user:pass@localhost:5432/audio）
- QUEUE_URL：Redis 队列（示例：redis://localhost:6379/0）
- STORAGE_ENDPOINT_URL / STORAGE_ACCESS_KEY / STORAGE_SECRET_KEY / STORAGE_BUCKET_NAME / STORAGE_REGION：S3 兼容对象存储配置（本地 MinIO 见下）
- REACT_APP_API_URL / REACT_APP_WS_URL：前端访问 API 与 WebSocket 的地址

## 本地运行（无需 Docker）

后端 API（SQLite 本地测试）
```bash
cd api
uvicorn app.main_sqlite:app --host 0.0.0.0 --port 8080 --reload
```

后端 API（PostgreSQL/Redis/MinIO，需自行准备服务）
```bash
cd api
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Worker（需要 Redis 队列）
```bash
cd worker
celery -A app.worker worker --loglevel=info
```

前端开发（可选）
```bash
cd frontend
npm ci
npm start
```

## Docker Compose 运行

```bash
# 确保已复制环境变量
cp .env.example .env

# 启动所有服务（API、Worker、Postgres、Redis、MinIO）
docker compose -f deploy/docker-compose.yml up -d

# 查看日志
docker compose -f deploy/docker-compose.yml logs -f --tail=200
```

## 测试

算法与存储本地测试：
```bash
python test_audio_processing.py
python test_storage_local.py
```

前端构建检查：
```bash
cd frontend
npm ci
npm run build
```

## CI 状态

本仓库已配置 GitHub Actions，提交或 PR 会自动执行：
- Python: 语法编译、算法与存储本地测试
- Node: 前端依赖安装与构建

[![CI](https://github.com/pain-ing/intelligent-audio-tuning-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/pain-ing/intelligent-audio-tuning-tool/actions/workflows/ci.yml)


详细技术方案请参考项目文档。
