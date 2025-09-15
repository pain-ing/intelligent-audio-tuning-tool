# Docker 环境设置指南

## 启动 Docker Desktop

### Windows 用户

1. **启动 Docker Desktop**
   - 在开始菜单搜索 "Docker Desktop" 并启动
   - 或者双击桌面上的 Docker Desktop 图标
   - 等待 Docker Desktop 完全启动（状态栏显示绿色）

2. **验证 Docker 状态**
   ```powershell
   docker info
   ```
   如果看到服务器信息（而不是连接错误），说明 Docker 已正常启动。

3. **启动完整环境**
   ```powershell
   cd deploy
   docker-compose build
   docker-compose up -d
   ```

### 如果 Docker Desktop 启动失败

1. **检查 WSL2**
   - Docker Desktop 需要 WSL2 支持
   - 在 PowerShell 中运行：`wsl --list --verbose`
   - 如果没有 WSL2，请安装：`wsl --install`

2. **检查 Hyper-V**
   - 确保 Windows 功能中启用了 Hyper-V
   - 控制面板 → 程序 → 启用或关闭 Windows 功能 → Hyper-V

3. **重启 Docker Desktop**
   - 右键点击系统托盘中的 Docker 图标
   - 选择 "Restart Docker Desktop"

## 快速测试（不需要 Docker）

如果 Docker 环境有问题，可以先运行本地测试：

```bash
python test_local.py
```

这将：
- 使用 SQLite 数据库（而不是 PostgreSQL）
- 启动本地 API 服务器
- 测试所有 API 端点
- 验证基本功能

## 完整环境启动步骤

1. **确保 Docker Desktop 运行**
   ```powershell
   docker --version
   docker info
   ```

2. **构建镜像**
   ```powershell
   cd deploy
   docker-compose build
   ```

3. **启动服务**
   ```powershell
   docker-compose up -d
   ```

4. **查看日志**
   ```powershell
   docker-compose logs -f
   ```

5. **测试服务**
   ```powershell
   curl http://localhost:8080/health
   ```

## 服务端口

- API: http://localhost:8080
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO: http://localhost:9000 (API), http://localhost:9001 (Console)

## 常见问题

### 端口冲突
如果端口被占用，修改 `deploy/docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8081:8080"  # 改为 8081
```

### 内存不足
Docker Desktop 默认内存限制可能不够，建议设置为至少 4GB：
- Docker Desktop → Settings → Resources → Memory

### 网络问题
如果容器间无法通信，重启 Docker Desktop 或重置网络：
```powershell
docker network prune
```
