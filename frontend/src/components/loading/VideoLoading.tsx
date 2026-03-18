import type { LoadingAnimationProps } from './types';
import './VideoLoading.css';

function VideoLoading({
  message = '正在加载...',
  videoSrc,
  muted = true,
  loop = true,
  autoPlay = true,
}: LoadingAnimationProps) {
  const videoPath = videoSrc || '/videos/loading.mp4';

  return (
    <div className="video-loading-screen">
      <div className="video-loading-backdrop" />

      <div className="video-loading-container">
        <video
          className="video-loading-player"
          src={videoPath}
          autoPlay={autoPlay}
          muted={muted}
          loop={loop}
          playsInline
          onError={(e) => {
            console.error('视频加载失败:', e);
          }}
        >
          您的浏览器不支持视频播放
        </video>
      </div>

      {message && (
        <div className="video-loading-content">
          <p className="video-loading-text">{message}</p>
        </div>
      )}
    </div>
  );
}

export default VideoLoading;
