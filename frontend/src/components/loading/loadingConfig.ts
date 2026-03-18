import type { LoadingAnimationComponent } from './types';

export const VIDEO_LOADING_CONFIG = {
  videoSrc: '/videos/loading.mp4',
  muted: true,
  loop: true,
  autoPlay: true,
};

export type LoadingAnimationType = 'sakura' | 'simple' | 'video';

export const DEFAULT_LOADING_TYPE: LoadingAnimationType = 'sakura';

export const loadLoadingAnimation = async (
  type: LoadingAnimationType
): Promise<LoadingAnimationComponent> => {
  switch (type) {
    case 'simple':
      return (await import('./SimpleLoading')).default;
    case 'video':
      return (await import('./VideoLoading')).default;
    case 'sakura':
    default:
      return (await import('./SakuraLoading')).default;
  }
};
