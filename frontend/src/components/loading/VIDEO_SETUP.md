# 视频加载动画设置指南

## 📋 概述

视频加载动画提供了更丰富、更专业的视觉体验，可以在加载时播放品牌视频、过渡动画或自定义加载视频。

## 🚀 快速开始

### 步骤 1：准备视频文件

1. **创建视频目录**
   ```
   frontend/public/videos/
   ```

2. **准备视频文件**
   - 推荐格式：MP4（兼容性最好）
   - 推荐分辨率：1920x1080 或 1280x720
   - 推荐时长：3-10 秒（循环播放）
   - 文件大小：尽量压缩，建议 < 5MB

3. **视频命名**
   - 默认文件名：`loading.mp4`
   - 或使用自定义文件名

### 步骤 2：配置视频路径

编辑 `components/loading/loadingConfig.ts`：

```typescript
export const VIDEO_LOADING_CONFIG = {
  // 修改为你的视频路径
  videoSrc: '/videos/loading.mp4',  // 或 '/videos/my-custom-loading.mp4'
  muted: true,      // 推荐 true，避免自动播放被阻止
  loop: true,       // 循环播放
  autoPlay: true,   // 自动播放
};
```

### 步骤 3：启用视频加载动画

在同一个文件中：

```typescript
export const DEFAULT_LOADING_TYPE = 'video';  // 改为 'video'
```

### 步骤 4：完成！

现在所有加载场景都会使用视频加载动画。

## 📁 视频文件位置

### 方式一：放在 public 目录（推荐）

```
frontend/
└── public/
    └── videos/
        └── loading.mp4
```

**优点**：
- 文件不会被 Vite 处理，直接复制到构建输出
- 可以通过 `/videos/loading.mp4` 直接访问
- 适合较大的视频文件

**使用**：
```typescript
videoSrc: '/videos/loading.mp4'
```

### 方式二：放在 assets 目录

```
frontend/
└── src/
    └── assets/
        └── videos/
            └── loading.mp4
```

**优点**：
- 会被 Vite 处理，可以优化
- 支持导入语法

**使用**：
```typescript
import loadingVideo from '@/assets/videos/loading.mp4';
// 然后在组件中使用
videoSrc: loadingVideo
```

## 🎬 视频要求

### 格式要求

- **推荐格式**：MP4 (H.264 编码)
- **备选格式**：WebM, OGG
- **不推荐**：AVI, MOV（文件大，兼容性差）

### 技术规格

| 属性 | 推荐值 | 说明 |
|------|--------|------|
| 分辨率 | 1920x1080 | 全屏显示，保持清晰 |
| 帧率 | 24-30 fps | 流畅播放 |
| 时长 | 3-10 秒 | 循环播放，不要太长 |
| 文件大小 | < 5MB | 快速加载 |
| 宽高比 | 16:9 | 适配大多数屏幕 |

### 内容建议

- ✅ 品牌 Logo 动画
- ✅ 游戏主题过渡动画
- ✅ 抽象几何动画
- ✅ 粒子效果动画
- ❌ 避免包含重要信息（可能被跳过）
- ❌ 避免过于复杂（影响性能）

## 🔧 高级配置

### 自定义视频路径

```typescript
// 在 loadingConfig.ts 中
export const VIDEO_LOADING_CONFIG = {
  videoSrc: '/videos/custom-loading.mp4',
  muted: true,
  loop: true,
  autoPlay: true,
};
```

### 动态切换视频

```tsx
import LoadingScreen from '@/components/loading';

function MyComponent() {
  return (
    <LoadingScreen 
      message="正在加载..."
      videoSrc="/videos/special-loading.mp4"  // 覆盖默认配置
    />
  );
}
```

### 控制播放选项

```tsx
<LoadingScreen 
  message="正在加载..."
  videoSrc="/videos/loading.mp4"
  muted={false}    // 有声音
  loop={true}      // 循环播放
  autoPlay={true}  // 自动播放
/>
```

## 🐛 常见问题

### Q1: 视频不播放？

**可能原因**：
1. 视频路径错误
2. 浏览器阻止自动播放（需要 muted: true）
3. 视频格式不支持

**解决方法**：
- 检查视频路径是否正确
- 确保 `muted: true`
- 使用 MP4 格式（H.264 编码）

### Q2: 视频加载慢？

**解决方法**：
- 压缩视频文件（使用 HandBrake 等工具）
- 降低分辨率（720p 通常足够）
- 减少视频时长
- 使用 CDN 托管视频

### Q3: 视频不循环？

**检查**：
- 确保 `loop: true`
- 检查视频文件本身是否支持循环

### Q4: 移动端不播放？

**解决方法**：
- 添加 `playsInline` 属性（已包含）
- 确保视频格式兼容（MP4）
- 检查移动浏览器限制

## 💡 最佳实践

1. **视频优化**
   - 使用视频压缩工具（如 HandBrake）
   - 选择合适的分辨率（不需要 4K）
   - 控制文件大小（< 5MB）

2. **性能考虑**
   - 视频应该快速加载
   - 避免过于复杂的动画
   - 考虑使用预加载

3. **用户体验**
   - 视频应该与游戏主题一致
   - 保持简洁，不要分散注意力
   - 确保加载文本清晰可见

4. **兼容性**
   - 使用 MP4 格式确保最大兼容性
   - 提供备用加载动画（如果视频失败）

## 📝 示例

### 基本使用

```tsx
import LoadingScreen from '@/components/loading';

if (loading) {
  return <LoadingScreen message="正在连接服务器..." />;
}
```

### 自定义视频

```tsx
<LoadingScreen 
  message="正在加载存档..."
  videoSrc="/videos/save-loading.mp4"
/>
```

## 🔄 切换回其他加载动画

如果不想使用视频加载动画，只需修改配置：

```typescript
// loadingConfig.ts
export const DEFAULT_LOADING_TYPE = 'sakura';  // 或 'simple'
```

---

*最后更新：2026-01-12*
