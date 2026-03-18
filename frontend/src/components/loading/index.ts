/**
 * 加载动画模块
 * 
 * 使用说明：
 * 1. 导入 LoadingScreen 组件使用
 * 2. 要更换加载动画，只需修改 loadingConfig.ts 中的配置
 * 3. 添加新的加载动画：创建新组件并实现 LoadingAnimationProps 接口
 * 
 * 视频加载动画使用：
 * 1. 将视频文件放在 public/videos/ 目录
 * 2. 在 loadingConfig.ts 中配置视频路径
 * 3. 设置 DEFAULT_LOADING_TYPE = 'video'
 */

export { default } from './LoadingScreen';
export { default as LoadingScreen } from './LoadingScreen';
export { default as SakuraLoading } from './SakuraLoading';
export { default as SimpleLoading } from './SimpleLoading';
export { default as VideoLoading } from './VideoLoading';
export type { LoadingAnimationProps } from './types';
export { VIDEO_LOADING_CONFIG, DEFAULT_LOADING_TYPE } from './loadingConfig';
