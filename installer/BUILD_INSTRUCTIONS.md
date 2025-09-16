# AudioTuner Desktop 构建说明

## 项目概述

AudioTuner是一个智能音频调音工具，采用混合架构：
- **前端**: React应用 (frontend目录)
- **后端**: FastAPI Python应用 (src、api、worker目录)  
- **桌面包装**: Electron应用 (packaging/desktop目录)
- **构建目标**: Windows Portable EXE文件

## 当前状态

✅ **可执行文件已生成**: `AudioTuner-Desktop.exe` (约251MB)

这是一个完整的便携式桌面应用程序，包含：
- Electron前端界面
- 嵌入式Python运行时
- 所有必要的依赖项
- FFmpeg音频处理工具

## 快速测试

运行以下命令测试现有的exe文件：
```bash
test_exe.bat
```

## 重新构建说明

### 环境要求

1. **Node.js** (v14+) 和 npm
2. **Python** (v3.8+)
3. **Windows** 操作系统

### 构建步骤

#### 方法1: 使用批处理脚本 (推荐)

```bash
cd packaging/desktop
build.bat
```

这个脚本会自动：
1. 检查环境依赖
2. 构建React前端
3. 安装Electron依赖
4. 打包桌面应用
5. 生成可执行文件

#### 方法2: 手动构建

1. **构建前端**:
```bash
cd frontend
npm install
npm run build
```

2. **构建桌面应用**:
```bash
cd packaging/desktop
npm install
npm run build
```

3. **查找生成的exe文件**:
生成的文件通常在以下目录之一：
- `packaging/desktop/dist_rf5/`
- `packaging/desktop/dist/`
- `packaging/desktop/release/`

### 构建配置

主要配置文件：
- `packaging/desktop/package.json` - Electron构建配置
- `packaging/desktop/src/main.js` - Electron主进程
- `frontend/package.json` - React前端配置

### 故障排除

#### 常见问题

1. **npm install失败**:
   - 清理node_modules: `rmdir /s /q node_modules`
   - 使用--legacy-peer-deps: `npm install --legacy-peer-deps`
   - 尝试使用yarn: `yarn install`

2. **Electron文件锁定**:
   - 关闭所有Electron进程
   - 重启命令行
   - 使用管理员权限运行

3. **Python依赖问题**:
   - 确保Python在PATH中
   - 检查requirements.txt中的依赖

4. **前端构建失败**:
   - 检查Node.js版本
   - 清理npm缓存: `npm cache clean --force`

#### 日志位置

- 构建日志: 控制台输出
- 应用日志: `%USERPROFILE%\.audio_tuner\app.log`
- Electron日志: 开发者工具控制台

### 高级配置

#### 修改应用信息

编辑 `packaging/desktop/package.json`:
```json
{
  "name": "audio-tuner-desktop",
  "version": "1.0.0",
  "description": "Audio Tuner Desktop Application",
  "build": {
    "appId": "com.audiotuner.desktop",
    "productName": "Audio Tuner"
  }
}
```

#### 添加图标

将图标文件放在 `packaging/desktop/resources/icon.png`

#### 修改输出目录

在package.json中修改：
```json
{
  "build": {
    "directories": {
      "output": "dist_custom"
    }
  }
}
```

## 部署说明

生成的exe文件是完全便携的，可以：
1. 直接运行，无需安装
2. 复制到任何Windows机器上使用
3. 通过网络共享分发

### 系统要求

- Windows 7/8/10/11 (64位)
- 至少2GB RAM
- 500MB可用磁盘空间

### 首次运行

应用程序会在用户目录创建配置文件夹：
`%USERPROFILE%\.audio_tuner\`

包含：
- 配置文件
- 本地数据库
- 日志文件
- 临时文件

## 开发说明

### 项目结构

```
Mituanapp2/
├── frontend/                 # React前端
├── src/                     # Python后端主代码
├── api/                     # API服务
├── worker/                  # 后台任务处理
├── packaging/desktop/       # Electron桌面打包
│   ├── src/main.js         # Electron主进程
│   ├── package.json        # 构建配置
│   ├── build.bat          # 构建脚本
│   └── vendor/            # 嵌入式依赖
└── AudioTuner-Desktop.exe  # 生成的可执行文件
```

### 开发模式

启动开发服务器：
```bash
# 后端
cd src
python main.py

# 前端
cd frontend
npm start

# Electron (开发模式)
cd packaging/desktop
npm run dev
```

### 调试

1. **后端调试**: 查看Python控制台输出
2. **前端调试**: 浏览器开发者工具
3. **Electron调试**: Electron开发者工具 (Ctrl+Shift+I)

## 更新说明

要更新应用程序：
1. 修改源代码
2. 重新运行构建脚本
3. 测试新的exe文件
4. 分发更新版本

版本号在 `packaging/desktop/package.json` 中管理。
