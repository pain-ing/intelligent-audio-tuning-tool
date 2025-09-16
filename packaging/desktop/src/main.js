const { app, BrowserWindow, Menu, shell, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// 尝试加载electron-log，如果失败则使用console
let log;
try {
  log = require('electron-log');
  log.transports.file.level = 'info';
  log.transports.console.level = 'debug';
} catch (error) {
  // 如果electron-log不可用，使用console作为备选
  log = {
    info: console.log,
    error: console.error,
    debug: console.log,
    warn: console.warn
  };
}

class AudioTunerApp {
  constructor() {
    this.mainWindow = null;
    this.apiProcess = null;
    this.isDev = process.argv.includes('--dev') || !app.isPackaged;
    this.apiPort = 8080;
    this.apiHost = '127.0.0.1';
    
    // 资源路径
    this.resourcesPath = this.isDev 
      ? path.join(__dirname, '..', '..', '..')
      : process.resourcesPath;
    
    // Python 可执行文件路径
    if (this.isDev) {
      const vendorPython = path.join(__dirname, '..', 'vendor', 'python', 'python.exe');
      this.pythonPath = fs.existsSync(vendorPython) ? vendorPython : 'python'; // 优先使用内置 Python，其次系统 Python
    } else {
      this.pythonPath = path.join(this.resourcesPath, 'python', 'python.exe');
    }

    // 使用重构后的主应用入口
    this.apiPath = path.join(this.resourcesPath, 'src');
    this.frontendPath = path.join(this.resourcesPath, 'frontend');

    log.info('Audio Tuner Desktop starting...');
    log.info(`Resources path: ${this.resourcesPath}`);
    log.info(`Python path: ${this.pythonPath}`);
    log.info(`API path: ${this.apiPath}`);
  }

  async createWindow() {
    // 创建主窗口
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 800,
      minHeight: 600,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: path.join(__dirname, 'preload.js')
      },
      icon: path.join(__dirname, '..', 'resources', 'icon.png'),
      show: false,
      titleBarStyle: 'default'
    });

    // 设置菜单
    this.createMenu();

    // 窗口事件
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
      if (this.isDev) {
        this.mainWindow.webContents.openDevTools();
      }
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // 处理外部链接
    this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: 'deny' };
    });

    // 启动API服务器
    await this.startApiServer();

    // 等待API服务器启动
    await this.waitForApiServer();

    // 加载前端
    const frontendUrl = `http://${this.apiHost}:${this.apiPort}`;
    log.info(`Loading frontend from: ${frontendUrl}`);
    
    try {
      await this.mainWindow.loadURL(frontendUrl);
    } catch (error) {
      log.error('Failed to load frontend:', error);
      // 显示错误页面
      await this.mainWindow.loadFile(path.join(__dirname, 'error.html'));
    }
  }

  async startApiServer() {
    if (this.apiProcess) {
      log.warn('API server already running');
      return;
    }

    log.info('Starting API server...');

    try {
      // 设置环境变量
      const userData = app.getPath('userData');
      const dataDir = path.join(userData, 'audio_tuner');
      try { fs.mkdirSync(dataDir, { recursive: true }); } catch (e) { /* ignore */ }
      const sqlitePath = path.join(dataDir, 'app.db').replace(/\\/g, '/');
      const env = {
        ...process.env,
        APP_MODE: 'desktop',
        STORAGE_MODE: 'local',
        CACHE_MODE: 'local',
        PYTHONPATH: this.apiPath,
        RESOURCES_PATH: this.resourcesPath,  // 添加资源路径
        DATA_DIR: dataDir,
        DATABASE_URL: `sqlite:///${sqlitePath}`,
        OPEN_BROWSER: 'false'  // 不让Python自动打开浏览器
      };

      // 添加FFmpeg到PATH（开发模式若存在也添加）
      const ffmpegDevPath = path.join(__dirname, '..', 'vendor', 'ffmpeg');
      if (!this.isDev) {
        const ffmpegPath = path.join(this.resourcesPath, 'ffmpeg');
        env.PATH = `${ffmpegPath};${env.PATH}`;
      } else if (fs.existsSync(ffmpegDevPath)) {
        env.PATH = `${ffmpegDevPath};${env.PATH}`;
      }

      // 启动Python API服务器 - 使用重构后的桌面版入口
      const mainDesktopPath = path.join(this.resourcesPath, 'src', 'desktop_main.py');

      log.info(`Spawning Python process:`);
      log.info(`  Python executable: ${this.pythonPath}`);
      log.info(`  Script path: ${mainDesktopPath}`);
      log.info(`  Working directory: ${this.apiPath}`);
      log.info(`  Environment variables:`);
      log.info(`    APP_MODE: ${env.APP_MODE}`);
      log.info(`    STORAGE_MODE: ${env.STORAGE_MODE}`);
      log.info(`    CACHE_MODE: ${env.CACHE_MODE}`);
      log.info(`    PYTHONPATH: ${env.PYTHONPATH}`);
      log.info(`    PATH: ${env.PATH}`);

      // 检查文件是否存在（仅在打包环境下检查 Python 路径）
      if (!this.isDev && !fs.existsSync(this.pythonPath)) {
        throw new Error(`Python executable not found: ${this.pythonPath}`);
      }
      if (!fs.existsSync(mainDesktopPath)) {
        throw new Error(`Main script not found: ${mainDesktopPath}`);
      }

      this.apiProcess = spawn(this.pythonPath, [mainDesktopPath], {
        env,
        cwd: this.resourcesPath,  // 使用资源根目录作为工作目录
        stdio: ['pipe', 'pipe', 'pipe']
      });

      // 日志处理
      this.apiProcess.stdout.on('data', (data) => {
        log.info(`API: ${data.toString().trim()}`);
      });

      this.apiProcess.stderr.on('data', (data) => {
        log.error(`API Error: ${data.toString().trim()}`);
      });

      this.apiProcess.on('close', (code) => {
        log.info(`API server exited with code ${code}`);
        this.apiProcess = null;
      });

      this.apiProcess.on('error', (error) => {
        log.error('Failed to start API server:', error);
        this.showErrorDialog('启动失败', '无法启动音频处理服务，请检查安装是否完整。');
      });

      log.info('API server started');

    } catch (error) {
      log.error('Error starting API server:', error);
      throw error;
    }
  }

  async waitForApiServer(maxAttempts = 30) {
    log.info('Waiting for API server to be ready...');

    const http = require('http');

    for (let i = 0; i < maxAttempts; i++) {
      try {
        await new Promise((resolve, reject) => {
          const req = http.get(`http://${this.apiHost}:${this.apiPort}/`, (res) => {
            if (res.statusCode === 200) {
              log.info('API server is ready');
              resolve(true);
            } else {
              reject(new Error(`HTTP ${res.statusCode}`));
            }
          });

          req.on('error', (error) => {
            reject(error);
          });

          req.setTimeout(2000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
          });
        });

        return true;
      } catch (error) {
        log.debug(`API check attempt ${i + 1}/${maxAttempts}: ${error.message}`);
      }

      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    throw new Error('API server failed to start within timeout');
  }

  stopApiServer() {
    if (this.apiProcess) {
      log.info('Stopping API server...');
      this.apiProcess.kill('SIGTERM');
      
      // 强制杀死进程（如果需要）
      setTimeout(() => {
        if (this.apiProcess) {
          this.apiProcess.kill('SIGKILL');
        }
      }, 5000);
    }
  }

  createMenu() {
    const template = [
      {
        label: '文件',
        submenu: [
          {
            label: '新建项目',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
              // TODO: 实现新建项目功能
            }
          },
          { type: 'separator' },
          {
            label: '退出',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => {
              app.quit();
            }
          }
        ]
      },
      {
        label: '编辑',
        submenu: [
          { role: 'undo', label: '撤销' },
          { role: 'redo', label: '重做' },
          { type: 'separator' },
          { role: 'cut', label: '剪切' },
          { role: 'copy', label: '复制' },
          { role: 'paste', label: '粘贴' }
        ]
      },
      {
        label: '视图',
        submenu: [
          { role: 'reload', label: '重新加载' },
          { role: 'forceReload', label: '强制重新加载' },
          { role: 'toggleDevTools', label: '开发者工具' },
          { type: 'separator' },
          { role: 'resetZoom', label: '实际大小' },
          { role: 'zoomIn', label: '放大' },
          { role: 'zoomOut', label: '缩小' },
          { type: 'separator' },
          { role: 'togglefullscreen', label: '全屏' }
        ]
      },
      {
        label: '帮助',
        submenu: [
          {
            label: '关于',
            click: () => {
              dialog.showMessageBox(this.mainWindow, {
                type: 'info',
                title: '关于 Audio Tuner',
                message: 'Audio Tuner Desktop v1.0.0',
                detail: '智能音频调音工具桌面版\n\n基于深度学习的音频风格迁移技术'
              });
            }
          }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  showErrorDialog(title, message) {
    if (this.mainWindow) {
      dialog.showErrorBox(title, message);
    }
  }
}

// 应用实例
const audioTunerApp = new AudioTunerApp();

// 应用事件
app.whenReady().then(() => {
  audioTunerApp.createWindow();
});

app.on('window-all-closed', () => {
  audioTunerApp.stopApiServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    audioTunerApp.createWindow();
  }
});

app.on('before-quit', () => {
  audioTunerApp.stopApiServer();
});

// IPC 处理
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('show-save-dialog', async () => {
  const result = await dialog.showSaveDialog(audioTunerApp.mainWindow, {
    filters: [
      { name: 'Audio Files', extensions: ['wav', 'mp3', 'flac'] }
    ]
  });
  return result;
});

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  log.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  log.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
