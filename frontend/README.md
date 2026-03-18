# No End Story - 前端项目

基于 React + TypeScript + Vite 构建的现代化前端应用。

## 技术栈

- **React 19** - UI 框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **React Router** - 路由管理
- **Axios** - HTTP 客户端
- **Ant Design** - UI 组件库
- **@ant-design/icons** - 图标库
- **Electron** - 桌面应用框架

## 项目结构

```
frontend/
├── src/
│   ├── components/      # 通用组件
│   │   ├── Layout.tsx   # 布局组件
│   │   └── ...
│   ├── pages/           # 页面组件
│   │   ├── Home.tsx     # 首页
│   │   ├── Game.tsx     # 游戏页面
│   │   └── NotFound.tsx # 404页面
│   ├── router/          # 路由配置
│   │   └── index.tsx
│   ├── services/        # API服务
│   │   └── api.ts       # Axios配置
│   ├── hooks/           # 自定义Hooks
│   ├── contexts/        # Context API
│   ├── utils/           # 工具函数
│   ├── types/           # TypeScript类型定义
│   ├── config/          # 配置文件
│   │   └── theme.ts     # Ant Design主题配置
│   ├── App.tsx          # 根组件
│   └── main.tsx         # 入口文件
├── public/              # 静态资源
├── package.json
├── tsconfig.json        # TypeScript配置
└── vite.config.ts       # Vite配置
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将在 `http://localhost:3000` 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

### Electron 桌面应用

#### 开发模式（Electron）

```bash
npm run electron:dev
```

这会同时启动 Vite 开发服务器和 Electron 窗口。

#### 打包桌面应用

```bash
# 构建并打包（生成安装程序）
npm run electron:build

# 只打包不构建安装程序（用于测试）
npm run electron:pack
```

打包后的文件会在 `release/` 目录下：
- **Windows**: `.exe` 安装程序
- **macOS**: `.dmg` 安装包
- **Linux**: `AppImage` 可执行文件

## 环境变量

创建 `.env` 文件（参考 `.env.example`）：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=No End Story
```

## 功能特性

- ✅ 路由管理（React Router）
- ✅ API 请求封装（Axios）
- ✅ TypeScript 类型支持
- ✅ 路径别名配置（@/）
- ✅ 开发代理配置
- ✅ 响应式布局
- ✅ 基础页面结构
- ✅ Ant Design UI 组件库集成
- ✅ 中文国际化配置
- ✅ 主题定制支持
- ✅ Electron 桌面应用支持
- ✅ 跨平台打包（Windows/Mac/Linux）

## 开发说明

### 路径别名

项目配置了路径别名 `@`，指向 `src` 目录：

```typescript
import Layout from '@/components/Layout';
import { formatDate } from '@/utils';
```

### API 调用

使用封装好的 `api` 实例：

```typescript
import api from '@/services/api';

// GET 请求
const data = await api.get('/users');

// POST 请求
const result = await api.post('/users', { name: 'John' });
```

### 添加新页面

1. 在 `src/pages/` 创建页面组件
2. 在 `src/router/index.tsx` 添加路由配置

### 使用 Ant Design 组件

项目已集成 Ant Design，可以直接使用所有组件：

```typescript
import { Button, Card, Input } from 'antd';
import { UserOutlined } from '@ant-design/icons';

function MyComponent() {
  return (
    <Card>
      <Button type="primary" icon={<UserOutlined />}>
        按钮
      </Button>
    </Card>
  );
}
```

### 主题定制

主题配置在 `src/config/theme.ts`，可以修改颜色、字体、圆角等：

```typescript
export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff', // 主色
    borderRadius: 8,          // 圆角
  },
  // ...
};
```

## 下一步开发

- [ ] 集成后端 API
- [ ] 添加状态管理（如 Zustand 或 Redux）
- [ ] 实现用户认证
- [ ] 完善游戏界面
- [ ] 添加错误边界
- [ ] 实现加载状态
- [ ] 添加单元测试
