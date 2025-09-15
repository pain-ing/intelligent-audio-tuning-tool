# 智能音频调音工具 - 前端界面

基于 React 的现代化音频处理前端界面，提供直观的音频上传、处理和结果展示功能。

## 功能特性

### 🎵 音频处理
- **双模式支持**：A 模式（配对模式）和 B 模式（风格模式）
- **拖拽上传**：支持拖拽上传音频文件
- **实时进度**：显示处理进度和状态
- **AB 对比**：处理前后音频对比播放

### 📊 可视化分析
- **频谱图**：实时频谱分析和对比
- **EQ 曲线**：均衡器频率响应可视化
- **动态范围**：音频动态范围对比图表
- **关键指标**：LUFS、峰值、质量评分等

### ⚙️ 参数编辑
- **均衡器**：多段 EQ 参数调整
- **动态处理**：压缩和限制器参数
- **立体声**：立体声宽度调整
- **音高**：音高校正参数

### 💾 预设管理
- **预设保存**：保存常用处理参数
- **分类管理**：按用途分类预设
- **收藏功能**：标记常用预设
- **导入导出**：预设文件管理

## 技术栈

- **React 18** - 现代化前端框架
- **Ant Design** - 企业级 UI 组件库
- **ECharts** - 数据可视化图表
- **Axios** - HTTP 客户端
- **React Dropzone** - 文件拖拽上传
- **WaveSurfer.js** - 音频波形显示

## 快速开始

### 安装依赖
```bash
cd frontend
npm install
```

### 启动开发服务器
```bash
npm start
```

应用将在 http://localhost:3000 启动

### 构建生产版本
```bash
npm run build
```

## 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── components/         # React 组件
│   │   ├── AudioProcessor.js    # 主处理界面
│   │   ├── FileUploader.js      # 文件上传组件
│   │   ├── AudioPlayer.js       # 音频播放器
│   │   ├── VisualizationPanel.js # 可视化面板
│   │   ├── ParameterEditor.js   # 参数编辑器
│   │   └── PresetManager.js     # 预设管理
│   ├── services/           # API 服务
│   │   └── api.js              # API 接口封装
│   ├── App.js              # 主应用组件
│   ├── App.css             # 应用样式
│   ├── index.js            # 应用入口
│   └── index.css           # 全局样式
├── package.json            # 项目配置
└── README.md              # 项目说明
```

## 组件说明

### AudioProcessor
主要的音频处理界面，包含：
- 模式选择（A/B 模式）
- 文件上传区域
- 处理控制按钮
- 状态显示和进度条
- 结果展示区域

### FileUploader
文件上传组件，支持：
- 拖拽上传
- 文件类型验证
- 上传进度显示
- 文件信息展示

### AudioPlayer
音频播放器组件，提供：
- 播放/暂停控制
- 进度条拖拽
- 音量调节
- 时间显示

### VisualizationPanel
可视化分析面板，包含：
- 关键指标统计
- EQ 频率响应图
- 频谱对比图
- 动态范围图

### ParameterEditor
参数编辑器，支持：
- EQ 参数调整
- 动态处理参数
- 立体声参数
- 音高调整参数

### PresetManager
预设管理界面，提供：
- 预设列表展示
- 新建/编辑预设
- 预设分类管理
- 收藏功能

## API 集成

前端通过 `src/services/api.js` 与后端 API 通信：

```javascript
import { audioAPI } from './services/api';

// 创建处理任务
const job = await audioAPI.createJob({
  mode: 'A',
  ref_key: 'reference.wav',
  tgt_key: 'target.wav'
});

// 查询任务状态
const status = await audioAPI.getJobStatus(job.job_id);
```

## 环境配置

创建 `.env` 文件配置环境变量：

```env
REACT_APP_API_URL=http://localhost:8080
REACT_APP_WS_URL=ws://localhost:8080
```

## 开发指南

### 添加新组件
1. 在 `src/components/` 目录创建组件文件
2. 使用 Ant Design 组件保持界面一致性
3. 添加适当的 PropTypes 类型检查
4. 编写组件文档和使用示例

### 样式规范
- 使用 Ant Design 的设计语言
- 保持响应式设计
- 使用 CSS-in-JS 或 CSS Modules
- 遵循 BEM 命名规范

### 状态管理
- 使用 React Hooks 管理组件状态
- 复杂状态可考虑使用 Context API
- 异步操作使用 async/await

## 部署

### Docker 部署
```bash
# 构建镜像
docker build -t audio-frontend .

# 运行容器
docker run -p 3000:3000 audio-frontend
```

### Nginx 部署
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /var/www/html;
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://backend:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 故障排除

### 常见问题

1. **API 连接失败**
   - 检查后端服务是否启动
   - 确认 API URL 配置正确
   - 检查网络连接和防火墙设置

2. **文件上传失败**
   - 检查文件大小限制
   - 确认文件格式支持
   - 检查对象存储配置

3. **音频播放问题**
   - 确认浏览器支持音频格式
   - 检查音频文件是否损坏
   - 确认 CORS 配置正确

### 调试技巧
- 使用浏览器开发者工具查看网络请求
- 检查控制台错误信息
- 使用 React Developer Tools 调试组件状态

## 贡献指南

1. Fork 项目仓库
2. 创建功能分支
3. 提交代码变更
4. 创建 Pull Request
5. 等待代码审查

## 许可证

MIT License
