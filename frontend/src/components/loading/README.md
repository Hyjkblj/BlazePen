# 加载动画系统使用指南

## 📋 概述

这是一个可替换的加载动画系统，允许你轻松地在不同的加载动画之间切换，而无需修改使用加载动画的代码。

## 🚀 快速开始

### 基本使用

```tsx
import LoadingScreen from '@/components/loading';

function MyComponent() {
  const [loading, setLoading] = useState(false);

  if (loading) {
    return <LoadingScreen message="正在加载..." />;
  }

  return <div>内容</div>;
}
```

## 🔄 更换加载动画

### 方法一：修改配置文件（推荐）

编辑 `loadingConfig.ts` 文件：

```typescript
// 修改默认加载动画类型
export const DEFAULT_LOADING_TYPE = 'video'; // 推荐使用 'video'

// 如果使用视频加载，还需要配置视频路径
export const VIDEO_LOADING_CONFIG = {
  videoSrc: '/videos/loading.mp4',  // 你的视频文件路径
  muted: true,
  loop: true,
  autoPlay: true,
};
```

就这么简单！所有使用 `LoadingScreen` 的地方都会自动使用新的加载动画。

### 方法二：添加新的加载动画

1. **创建新的加载动画组件**

   在 `loading/` 目录下创建新文件，例如 `MyCustomLoading.tsx`：

   ```tsx
   import { LoadingAnimationProps } from './types';
   import './MyCustomLoading.css';

   function MyCustomLoading({ message = '加载中...' }: LoadingAnimationProps) {
     return (
       <div className="my-custom-loading">
         {/* 你的自定义加载动画 */}
         <div>{message}</div>
       </div>
     );
   }

   export default MyCustomLoading;
   ```

2. **注册到配置**

   在 `loadingConfig.ts` 中添加：

   ```typescript
   import MyCustomLoading from './MyCustomLoading';

   export const LOADING_ANIMATIONS = {
     video: VideoLoading,
     sakura: SakuraLoading,
     simple: SimpleLoading,
     custom: MyCustomLoading, // 添加新的加载动画
   };

   export const DEFAULT_LOADING_TYPE = 'custom'; // 设置为默认
   ```

3. **完成！**

   现在所有地方都会使用你的自定义加载动画。

## 📁 文件结构

```
components/loading/
├── index.ts              # 导出入口
├── LoadingScreen.tsx     # 统一加载屏幕组件（根据配置选择动画）
├── loadingConfig.ts      # 配置文件（在这里切换加载动画）
├── types.ts              # TypeScript 类型定义
├── VideoLoading.tsx      # 视频加载动画（推荐）
├── VideoLoading.css      # 视频加载动画样式
├── SakuraLoading.tsx     # 樱花加载动画
├── SakuraLoading.css     # 樱花加载动画样式
├── SimpleLoading.tsx     # 简单加载动画（备用）
├── SimpleLoading.css     # 简单加载动画样式
├── README.md             # 使用文档
└── VIDEO_SETUP.md        # 视频加载动画设置指南
```

## 🎨 可用的加载动画

### 1. VideoLoading（视频加载动画）⭐ 推荐
- **类型**: `'video'`
- **特点**: 播放自定义视频，提供最丰富的视觉体验
- **适用场景**: 品牌展示、专业过渡动画、需要高质量视觉效果的场景
- **设置**: 查看 [VIDEO_SETUP.md](./VIDEO_SETUP.md) 了解详细设置步骤
- **优点**: 
  - 视觉效果最佳
  - 可以展示品牌 Logo 或主题动画
  - 更好的用户体验

### 2. SakuraLoading（樱花加载动画）
- **类型**: `'sakura'`
- **特点**: 三个旋转的樱花花瓣，带有加载点动画
- **适用场景**: 游戏主界面、需要视觉吸引力的场景

### 3. SimpleLoading（简单加载动画）
- **类型**: `'simple'`
- **特点**: 使用 Ant Design 的 Spin 组件，简洁高效
- **适用场景**: 需要快速加载、性能优先的场景

## 🔧 高级用法

### 动态切换加载动画

```tsx
import LoadingScreen from '@/components/loading';
import { getLoadingAnimation } from '@/components/loading/loadingConfig';

function MyComponent() {
  const [loadingType, setLoadingType] = useState('sakura');
  
  const CustomLoading = getLoadingAnimation(loadingType);
  
  return loading ? <CustomLoading message="加载中..." /> : <div>内容</div>;
}
```

### 自定义加载消息

```tsx
<LoadingScreen message="正在连接服务器..." />
<LoadingScreen message="正在加载存档..." />
<LoadingScreen message="正在初始化新故事..." />
```

### 使用视频加载动画

1. **准备视频文件**
   - 将视频放在 `public/videos/` 目录
   - 推荐格式：MP4，分辨率 1920x1080，时长 3-10 秒

2. **配置视频路径**
   ```typescript
   // loadingConfig.ts
   export const VIDEO_LOADING_CONFIG = {
     videoSrc: '/videos/loading.mp4',  // 你的视频路径
     muted: true,
     loop: true,
     autoPlay: true,
   };
   ```

3. **启用视频加载**
   ```typescript
   export const DEFAULT_LOADING_TYPE = 'video';
   ```

详细设置请查看 [VIDEO_SETUP.md](./VIDEO_SETUP.md)

## 💡 最佳实践

1. **统一使用 LoadingScreen**
   - 不要直接导入具体的加载动画组件
   - 使用 `LoadingScreen` 组件，让系统自动选择

2. **通过配置切换**
   - 修改 `loadingConfig.ts` 来切换加载动画
   - 不要在使用的地方硬编码加载动画类型

3. **添加新动画时**
   - 确保实现 `LoadingAnimationProps` 接口
   - 添加对应的 CSS 文件
   - 在配置文件中注册

## 🐛 故障排除

### 加载动画不显示
- 检查 `loadingConfig.ts` 中的 `DEFAULT_LOADING_TYPE` 是否正确
- 确保对应的加载动画组件已正确导入

### 样式不生效
- 检查 CSS 文件是否正确导入
- 确保类名没有冲突

## 📝 示例

查看以下文件了解完整的使用示例：
- `pages/Home.tsx` - 首页使用示例
- `pages/FirstStep.tsx` - 第一步页面使用示例
