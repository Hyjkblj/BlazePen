import { useEffect, useState } from 'react';
import SakuraLoading from './SakuraLoading';
import { DEFAULT_LOADING_TYPE, loadLoadingAnimation, VIDEO_LOADING_CONFIG } from './loadingConfig';
import type { LoadingAnimationComponent, LoadingAnimationProps } from './types';

/**
 * 统一的加载屏幕组件
 *
 * 默认动画直接内联，其他可选动画按需加载，避免把所有实现都打进首包。
 */
function LoadingScreen(props: LoadingAnimationProps) {
  const [LoadingAnimation, setLoadingAnimation] = useState<LoadingAnimationComponent>(() => SakuraLoading);

  useEffect(() => {
    if (DEFAULT_LOADING_TYPE === 'sakura') {
      return;
    }

    let cancelled = false;

    void loadLoadingAnimation(DEFAULT_LOADING_TYPE).then((component) => {
      if (!cancelled) {
        setLoadingAnimation(() => component);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  if (DEFAULT_LOADING_TYPE === 'video' && !props.videoSrc) {
    return (
      <LoadingAnimation
        {...props}
        videoSrc={VIDEO_LOADING_CONFIG.videoSrc}
        muted={VIDEO_LOADING_CONFIG.muted}
        loop={VIDEO_LOADING_CONFIG.loop}
        autoPlay={VIDEO_LOADING_CONFIG.autoPlay}
      />
    );
  }

  return <LoadingAnimation {...props} />;
}

export default LoadingScreen;
