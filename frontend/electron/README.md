# Electron 配置说明

## 文件说明

- `main.js` - Electron 主进程文件，负责创建和管理应用窗口
- `preload.js` - 预加载脚本，用于在主进程和渲染进程之间安全地暴露API

## 开发模式

```bash
# 启动开发模式（同时启动Vite开发服务器和Electron）
npm run electron:dev
```

## 打包应用

```bash
# 构建并打包应用
npm run electron:build

# 只打包不构建安装程序（用于测试）
npm run electron:pack
```

打包后的文件会在 `release/` 目录下。

## 平台支持

- **Windows**: 生成 `.exe` 安装程序（NSIS）
- **macOS**: 生成 `.dmg` 安装包
- **Linux**: 生成 `AppImage` 可执行文件

## 注意事项

1. 开发环境会自动打开开发者工具
2. 生产环境会加载打包后的静态文件
3. 确保后端API在 `http://localhost:8000` 运行（或修改配置）
