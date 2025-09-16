# Audio Tuner Desktop 打包说明

## 概述

这个目录包含了将 Audio Tuner 项目打包成 Windows 桌面应用程序的完整配置和脚本。

## 架构说明

### 桌面版架构
- **Electron 主进程**: 管理应用窗口和生命周期
- **Python 后端**: 运行 FastAPI 服务器和音频处理逻辑
- **React 前端**: 用户界面，通过 HTTP API 与后端通信
- **本地存储**: 使用文件系统替代 MinIO，SQLite 替代 PostgreSQL
- **本地任务队列**: 使用 ThreadPoolExecutor 替代 Celery+Redis

### 文件结构
```
packaging/desktop/
├── src/
│   ├── main.js          # Electron 主进程
│   ├── preload.js       # 预加载脚本
│   └── error.html       # 错误页面
├── resources/           # 应用图标和资源
├── package.json         # Electron 配置
├── installer.nsh        # NSIS 安装器脚本
├── build.py            # 自动化构建脚本
└── README.md           # 本文件
```

## 构建要求

### 系统要求
- Windows 10/11 x64
- Node.js 16+ 和 npm
- Python 3.8+
- Git

### 依赖工具
- electron
- electron-builder
- NSIS (自动下载)

## 构建步骤

### 方法一：自动化构建（推荐）

```bash
# 进入打包目录
cd packaging/desktop

# 运行自动化构建脚本
python build.py
```

构建脚本会自动完成：
1. 构建前端 React 应用
2. 下载 Python 嵌入式运行时
3. 安装 Python 依赖包
4. 下载 FFmpeg 二进制文件
5. 安装 Electron 依赖
6. 构建 Electron 应用
7. 创建 NSIS 安装包

### 方法二：手动构建

```bash
# 1. 构建前端
cd ../../frontend
npm install
npm run build

# 2. 准备 Python 运行时（手动下载并解压到 python-runtime/）
# 下载地址: https://www.python.org/downloads/windows/

# 3. 准备 FFmpeg（手动下载并解压到 ffmpeg/）
# 下载地址: https://github.com/BtbN/FFmpeg-Builds/releases

# 4. 构建 Electron 应用
cd ../packaging/desktop
npm install
npm run build-win
```

## 配置说明

### package.json 配置
- `build.extraResources`: 指定要打包的资源文件
- `build.win.target`: Windows 构建目标（NSIS）
- `build.nsis`: NSIS 安装器配置

### 环境变量
桌面版使用以下环境变量：
- `APP_MODE=desktop`: 启用桌面模式
- `STORAGE_MODE=local`: 使用本地文件存储
- `CACHE_MODE=local`: 使用本地文件缓存

### 数据目录
用户数据存储在：
- Windows: `%APPDATA%\AudioTuner\`
  - `db.sqlite3`: SQLite 数据库
  - `objects/`: 音频文件存储
  - `cache/`: 缓存文件
  - `queue/`: 任务队列状态

## 安装包特性

### 安装器功能
- 一键安装，无需额外配置
- 自动创建桌面快捷方式
- 自动创建开始菜单项
- 支持自定义安装目录
- 卸载时可选保留用户数据

### 应用功能
- 自动启动后端服务
- 自动打开前端界面
- 优雅的错误处理和重试机制
- 完整的菜单栏和快捷键支持

## 故障排除

### 常见问题

1. **构建失败 - Python 依赖错误**
   - 确保网络连接正常
   - 检查 requirements.txt 文件是否存在
   - 尝试手动安装依赖

2. **构建失败 - 前端构建错误**
   - 检查 Node.js 版本
   - 清理 node_modules 并重新安装
   - 检查前端代码是否有语法错误

3. **运行时错误 - 端口占用**
   - 检查 8080 端口是否被占用
   - 修改 main.js 中的端口配置

4. **运行时错误 - Python 模块缺失**
   - 检查 Python 依赖是否正确安装
   - 验证 PYTHONPATH 设置

### 调试模式

开发时可以使用调试模式：
```bash
npm run dev
```

这会启用开发者工具并使用系统 Python 环境。

## 版本发布

### 版本号管理
版本号在 `package.json` 中定义，构建时会自动应用到：
- 安装包文件名
- 应用程序信息
- 关于对话框

### 发布检查清单
- [ ] 更新版本号
- [ ] 测试所有核心功能
- [ ] 验证安装/卸载流程
- [ ] 检查文件大小合理性
- [ ] 准备发布说明

## 技术细节

### Electron 进程通信
- 主进程管理 Python 子进程
- 渲染进程通过 HTTP API 与后端通信
- 使用 contextBridge 安全暴露 API

### 资源打包
- Python 运行时: 嵌入式版本，约 15MB
- FFmpeg: 静态链接版本，约 50MB
- 前端资源: 构建后的静态文件，约 2MB
- 总安装包大小: 约 100-150MB

### 性能优化
- 使用本地文件系统避免网络开销
- SQLite 数据库提供快速本地存储
- 多线程任务队列支持并发处理
- 自适应内存管理减少资源占用
