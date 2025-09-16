const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 应用信息
  getVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // 文件对话框
  showSaveDialog: () => ipcRenderer.invoke('show-save-dialog'),
  
  // 平台信息
  platform: process.platform,
  
  // 应用状态
  isDesktop: true
});

// 日志功能
contextBridge.exposeInMainWorld('logger', {
  info: (message) => console.log('[Desktop]', message),
  warn: (message) => console.warn('[Desktop]', message),
  error: (message) => console.error('[Desktop]', message)
});
