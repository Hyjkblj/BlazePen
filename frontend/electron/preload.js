const { contextBridge } = require('electron');

// 暴露受保护的方法给渲染进程
// 这里可以添加需要从主进程暴露给渲染进程的API
contextBridge.exposeInMainWorld('electronAPI', {
  // 示例：获取应用版本
  getVersion: () => process.versions.electron,
  
  // 可以在这里添加更多API
  // 例如：文件系统访问、系统通知等
});
