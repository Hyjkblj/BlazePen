# Electron 桌面应用设置指南

## ✅ 已完成配置

项目已成功配置 Electron 支持，可以将 React 应用打包成桌面应用。

## 📁 项目结构

```
frontend/
├── electron/
│   ├── main.js          # Electron 主进程
│   ├── preload.js       # 预加载脚本
│   └── README.md        # Electron 说明文档
├── src/                 # React 源代码（保持不变）
├── dist/                # 构建输出（打包时生成）
└── release/             # 打包后的应用（打包时生成）
```

## 🚀 快速开始

### 1. 安装依赖（如果还没安装）

```bash
cd frontend
npm install
```

### 2. 开发模式

启动 Electron 开发模式（同时启动 Vite 开发服务器和 Electron 窗口）：

```bash
npm run electron:dev
```

这会：
- 启动 Vite 开发服务器（http://localhost:3000）
- 等待服务器就绪后启动 Electron 窗口
- 自动打开开发者工具

### 3. 构建和打包

#### 构建生产版本

```bash
npm run build
```

这会生成 `dist/` 目录，包含打包后的静态文件。

#### 打包桌面应用

```bash
# 完整打包（生成安装程序）
npm run electron:build

# 仅打包不生成安装程序（用于测试）
npm run electron:pack
```

打包后的文件会在 `release/` 目录下：

- **Windows**: `No End Story Setup x.x.x.exe` (NSIS 安装程序)
- **macOS**: `No End Story-x.x.x.dmg` (DMG 安装包)
- **Linux**: `No End Story-x.x.x.AppImage` (AppImage 可执行文件)

## ⚙️ 配置说明

### Electron 主进程 (`electron/main.js`)

- 创建和管理应用窗口
- 开发环境：加载 `http://localhost:3000`
- 生产环境：加载 `dist/index.html`
- 自动处理窗口关闭和重新打开

### 预加载脚本 (`electron/preload.js`)

- 安全地暴露 API 给渲染进程
- 当前包含版本信息 API
- 可以根据需要添加更多 API

### 打包配置 (`package.json` 中的 `build` 字段)

- **appId**: `com.noendstory.app`
- **productName**: `No End Story`
- **输出目录**: `release/`
- **Windows**: NSIS 安装程序，支持自定义安装路径
- **macOS**: DMG 安装包，支持 Intel 和 Apple Silicon
- **Linux**: AppImage 可执行文件

## 🎨 添加应用图标

1. 在 `frontend/build/` 目录下创建图标文件：
   - `icon.ico` (Windows, 256x256)
   - `icon.icns` (macOS, 512x512)
   - `icon.png` (Linux, 512x512)

2. 图标会自动在打包时使用

## 🔧 常见问题

### 1. Electron 窗口显示空白

**原因**: Vite 开发服务器未启动或端口不对

**解决**: 
- 确保 `npm run dev` 可以正常启动
- 检查 `electron/main.js` 中的端口号（默认 3000）

### 2. 打包后应用无法连接后端

**原因**: 生产环境需要配置后端 API 地址

**解决**: 
- 修改 `src/services/api.ts` 中的 `baseURL`
- 或使用环境变量配置

### 3. 打包体积过大

**原因**: Electron 需要打包 Chromium 内核

**解决**: 
- 这是正常的，Electron 应用通常 100MB+
- 可以考虑使用 Tauri（更轻量，但需要 Rust）

## 📝 下一步

1. ✅ Electron 配置已完成
2. ⏳ 添加应用图标
3. ⏳ 配置后端 API 地址（生产环境）
4. ⏳ 测试打包和安装
5. ⏳ 配置自动更新（可选）

## 🔗 相关文档

- [Electron 官方文档](https://www.electronjs.org/docs)
- [electron-builder 文档](https://www.electron.build/)
- [Vite + Electron 最佳实践](https://vitejs.dev/guide/)

---

*最后更新：2026-01-12*
