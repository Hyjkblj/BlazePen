import type React from 'react';

/**
 * 加载动画组件属性类型
 * 所有加载动画组件都应该实现这个类型
 */
export interface LoadingAnimationProps {
  /** 加载提示文本 */
  message?: string;
  /** 自定义样式类名 */
  className?: string;
  /** 视频文件路径（仅视频加载动画使用） */
  videoSrc?: string;
  /** 是否静音播放（仅视频加载动画使用） */
  muted?: boolean;
  /** 是否循环播放（仅视频加载动画使用） */
  loop?: boolean;
  /** 是否自动播放（仅视频加载动画使用） */
  autoPlay?: boolean;
}

/**
 * 加载动画组件类型
 */
export type LoadingAnimationComponent = React.ComponentType<LoadingAnimationProps>;
