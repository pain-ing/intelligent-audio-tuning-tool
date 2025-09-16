# 智能音频调音工具 (Audio Style Matching Tool)

[![CI](https://github.com/pain-ing/intelligent-audio-tuning-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/pain-ing/intelligent-audio-tuning-tool/actions/workflows/ci.yml)
[![Download](https://img.shields.io/github/v/release/pain-ing/intelligent-audio-tuning-tool?label=download)](https://github.com/pain-ing/intelligent-audio-tuning-tool/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/pain-ing/intelligent-audio-tuning-tool/total?label=downloads)](https://github.com/pain-ing/intelligent-audio-tuning-tool/releases)


- 问题反馈 / 建议：https://github.com/pain-ing/intelligent-audio-tuning-tool/issues/new/choose （请选择 Bug 报告或功能需求模板）
- v1.0.1 里程碑：https://github.com/pain-ing/intelligent-audio-tuning-tool/milestone/1





## 下载与安装

- 稳定版发布页（v1.0.0）：https://github.com/pain-ing/intelligent-audio-tuning-tool/releases/tag/v1.0.0
- 直接下载（Windows 64 位，便携 ZIP，约 240 MB）：
  - https://github.com/pain-ing/intelligent-audio-tuning-tool/releases/download/v1.0.0/AudioTuner-Desktop-v1.0.0-Release.zip
- SHA256 校验：
  - ceaf311c217d8e51fd55c6e8c9b8e76fd470961d3c1045c53885727c2f370b92

使用方法：下载并解压 ZIP，双击运行解压目录中的 `AudioTuner-Desktop.exe` 即可。
最低要求：Windows 7/8/10/11（64 位）、2GB 内存、500MB 可用磁盘空间。


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

### 新增接口

- 列表（Keyset 分页）：
  - GET /jobs?user_id=<uuid>&status=<STATUS>&limit=20&cursor=<cursor>&created_after=<ISO8601>&created_before=<ISO8601>&updated_after=<ISO8601>&updated_before=<ISO8601>&sort_by=<created_at|updated_at>&order=<asc|desc>
  - 返回：{ items: [...], next_cursor }
  - items 字段：每项包含 id、user_id、mode、status、progress、created_at、updated_at、result_key、download_url（预签名，默认 1 小时有效）、error
  - 说明：cursor 与排序字段/方向绑定；切换排序会重置 cursor
- 状态统计（短 TTL 缓存）：
  - GET /jobs/stats?user_id=<uuid>&created_after=<ISO8601>&created_before=<ISO8601>
  - 返回：{ PENDING, ANALYZING, INVERTING, RENDERING, COMPLETED, FAILED }
- 重试失败任务：
  - POST /jobs/{job_id}/retry（仅 FAILED 可重试）
- POST /jobs/{job_id}/cancel（PENDING/ANALYZING/INVERTING/RENDERING 可取消）
- 详情：
  - GET /jobs/{job_id}（返回 download_url：预签名下载 URL，默认 1 小时有效）




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

- ENABLE_CACHE：启用 Redis 缓存（特征/渲染结果/统计），默认 true
- RENDER_MAX_WORKERS：渲染分块并行度（默认 1，建议 1～4）
- METRICS_LOG_DIR：Worker 指标日志目录，默认 /tmp/metrics
- OMP_NUM_THREADS / OPENBLAS_NUM_THREADS / MKL_NUM_THREADS / NUMEXPR_NUM_THREADS：限制数值库线程，避免与多进程叠加争抢


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

### 指标导出（Worker）

从 JSONL 指标日志导出 CSV/JSON 与汇总：
```bash
python worker/scripts/export_metrics.py --log-dir /tmp/metrics --out metrics_export
# 输出：metrics_export.csv / metrics_export.json / metrics_export.summary.json
```

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


## 常见问题（FAQ）

- Windows SmartScreen 警报：点击“更多信息”→“仍要运行”。
- 杀软/防护误报：加入白名单，或先校验 SHA256（见“下载与安装”）。
- 首次启动白屏/打不开：检查 8080 端口占用（`netstat -ano | findstr 8080`），释放后再试。
- 无法写入用户目录：以管理员身份运行，或将应用解压到具备写权限的目录。
- 解压路径含特殊字符：若异常，可移动到英文路径后再尝试。

## 故障诊断与日志

- 校验下载完整性（PowerShell）：
  ```powershell
  Get-FileHash -Algorithm SHA256 "AudioTuner-Desktop-v1.0.0-Release.zip"
  ```
- 检查端口占用：
  ```powershell
  netstat -ano | findstr 8080
  ```
- 日志与配置（若存在）：`%USERPROFILE%\.audio_tuner\`，可打包用于反馈：
  ```powershell
  Compress-Archive -Path "$env:USERPROFILE\.audio_tuner" -DestinationPath "$env:USERPROFILE\Desktop\audio_tuner_diag.zip" -Force
  ```
