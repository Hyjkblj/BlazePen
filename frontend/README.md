# No End Story Frontend

基于 `React 19 + TypeScript + Vite + Electron` 的前端应用。

## 技术栈

- `React 19`
- `TypeScript`
- `Vite`
- `React Router`
- `Axios`
- `Electron`

## 当前架构约定

- 页面负责路由装配与状态消费，业务流程优先放在 `src/flows`
- 通用能力放在 `src/contexts`、`src/hooks`、`src/services`
- UI 基础组件放在 `src/components`
- 运行时不依赖 `antd`，弹窗、提示、图标与静态资源展示均使用本地组件

## 目录结构

```text
frontend/
├─ src/
│  ├─ components/      # 通用 UI 组件
│  ├─ contexts/        # 跨页面上下文能力
│  ├─ flows/           # 页面流程编排
│  ├─ hooks/           # 复用 hooks
│  ├─ pages/           # 路由页面
│  ├─ router/          # 路由配置
│  ├─ services/        # API 与资源访问
│  ├─ storage/         # 本地持久化
│  ├─ types/           # 类型定义
│  ├─ utils/           # 工具函数
│  ├─ App.tsx
│  └─ main.tsx
├─ electron/           # Electron 主进程
├─ public/             # 静态资源
└─ package.json
```

## 开发命令

```bash
npm install
npm run dev
npm run lint
npm run build
npm run electron:dev
npm run electron:pack
npm run electron:build
```

默认开发地址为 `http://localhost:3000`。

## 环境变量

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=No End Story
```

## 开发建议

- 新增页面时，把页面编排与数据流放进 `src/flows`
- 需要全局提示时，优先使用 `useFeedback()`
- 需要弹窗时，优先使用 `ModalDialog`
- 需要静态图片时，优先使用 `StaticAssetImage` 或 `getStaticAssetUrl`
- 保持组件职责单一，避免页面直接依赖底层服务实现细节

## 后续建议

- 增加前端自动化测试
- 为关键流程补充错误边界
- 继续收敛页面样式中的重复结构
