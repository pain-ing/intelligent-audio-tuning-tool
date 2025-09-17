# 🛠️ AudioTuner 开发指南

## 📋 项目概述

AudioTuner 是一个智能音频调音工具，采用现代化的混合架构设计，支持桌面应用和云端部署。

### 🏗️ 技术架构

```
AudioTuner 架构图
├── 🎨 前端层 (React + Ant Design)
│   ├── 组件化设计
│   ├── 响应式布局
│   └── 深色主题
├── 🌐 API层 (FastAPI)
│   ├── RESTful API
│   ├── 异步处理
│   └── 自动文档生成
├── 🔧 服务层 (Python)
│   ├── 音频处理服务
│   ├── 任务管理服务
│   └── 存储服务
├── 🖥️ 桌面层 (pywebview/Electron)
│   ├── 原生窗口
│   ├── 系统集成
│   └── 离线支持
└── 💾 数据层 (SQLite/PostgreSQL)
    ├── 任务管理
    ├── 用户数据
    └── 缓存机制
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **Node.js**: 16+
- **操作系统**: Windows 10/11 (桌面版)

### 开发环境设置

```bash
# 1. 克隆项目
git clone https://github.com/pain-ing/intelligent-audio-tuning-tool.git
cd intelligent-audio-tuning-tool

# 2. 设置Python环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 设置前端环境
cd frontend
npm install
npm run build
cd ..

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件设置必要的配置

# 5. 启动开发服务器
python src/main.py
```

### 桌面应用开发

```bash
# 启动桌面应用开发模式
python src/desktop_app.py

# 构建桌面应用
python build_exe.py
```

## 📁 项目结构

```
AudioTuner/
├── frontend/                 # React前端应用
│   ├── src/
│   │   ├── components/       # React组件
│   │   ├── hooks/           # 自定义Hook
│   │   ├── services/        # API服务
│   │   └── utils/           # 工具函数
│   ├── public/              # 静态资源
│   └── build/               # 构建输出
├── src/                     # Python后端主代码
│   ├── core/                # 核心模块
│   ├── services/            # 服务层
│   ├── api/                 # API路由
│   ├── utils/               # 工具模块
│   └── desktop_app.py       # 桌面应用入口
├── worker/                  # 后台任务处理
├── api/                     # 兼容性API
├── packaging/               # 打包配置
├── tests/                   # 测试代码
└── docs/                    # 文档
```

## 🔧 开发规范

### 代码风格

#### Python代码规范
- 遵循 PEP 8 标准
- 使用类型注解
- 函数和类必须有文档字符串
- 单个函数不超过50行

```python
def process_audio(
    input_path: str, 
    output_path: str, 
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    处理音频文件
    
    Args:
        input_path: 输入音频文件路径
        output_path: 输出音频文件路径
        params: 处理参数
        
    Returns:
        处理结果字典，包含指标和状态信息
        
    Raises:
        AudioProcessingError: 音频处理失败时抛出
    """
    pass
```

#### JavaScript代码规范
- 使用 ES6+ 语法
- 组件使用函数式组件和Hooks
- 使用 JSDoc 注释
- 遵循 Airbnb 风格指南

```javascript
/**
 * 音频处理进度Hook
 * @param {Object} options - 配置选项
 * @returns {Object} 进度状态和控制函数
 */
const useAudioProgress = (options = {}) => {
  // Hook实现
};
```

### Git提交规范

使用约定式提交格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

类型说明：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

示例：
```
feat(audio): add real-time progress tracking

- Implement WebSocket-based progress updates
- Add cancellation support for long-running tasks
- Improve error handling and recovery

Closes #123
```

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_services.py

# 运行带覆盖率的测试
pytest --cov=src tests/

# 运行前端测试
cd frontend
npm test
```

### 测试编写规范

```python
import pytest
from unittest.mock import Mock, patch

class TestAudioService:
    """音频服务测试类"""
    
    @pytest.fixture
    def audio_service(self):
        """音频服务测试夹具"""
        return AudioService()
    
    @pytest.mark.asyncio
    async def test_analyze_features_success(self, audio_service, sample_audio_file):
        """测试音频特征分析成功场景"""
        # Given
        expected_features = {"stft": [...], "mel": [...]}
        
        # When
        result = await audio_service.analyze_features(sample_audio_file)
        
        # Then
        assert "stft" in result
        assert "mel" in result
        assert len(result["stft"]) > 0
```

## 🚀 部署指南

### 桌面应用部署

```bash
# 构建可执行文件
python build_exe.py

# 生成的文件
# - AudioTuner-Desktop-App.exe (主程序)
# - 桌面快捷方式
```

### 云端部署

```bash
# 使用Docker部署
docker-compose up -d

# 或手动部署
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

## 🔍 调试技巧

### 前端调试
- 使用浏览器开发者工具
- React DevTools扩展
- 网络面板监控API请求

### 后端调试
- 设置 `DEBUG=true` 环境变量
- 使用 `logging` 模块记录详细日志
- PyCharm/VSCode断点调试

### 桌面应用调试
- 设置 `webview.start(debug=True)`
- 查看控制台输出
- 使用日志文件分析问题

## 📚 API文档

启动应用后访问：
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### Pull Request检查清单

- [ ] 代码遵循项目规范
- [ ] 添加了必要的测试
- [ ] 测试全部通过
- [ ] 更新了相关文档
- [ ] 提交信息符合约定式提交格式

## 🐛 问题排查

### 常见问题

1. **端口占用**
   ```bash
   # 检查端口占用
   netstat -ano | findstr :8080
   # 杀死占用进程
   taskkill /PID <PID> /F
   ```

2. **依赖安装失败**
   ```bash
   # 清理缓存重新安装
   pip cache purge
   pip install -r requirements.txt --no-cache-dir
   ```

3. **前端构建失败**
   ```bash
   # 清理node_modules重新安装
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

## 📞 获取帮助

- 📧 邮箱: support@audiotuner.com
- 💬 讨论: GitHub Discussions
- 🐛 问题: GitHub Issues
- 📖 文档: 项目Wiki

---

**Happy Coding! 🎵✨**
