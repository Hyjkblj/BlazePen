import type { LoadingAnimationProps } from './types';
import './SakuraLoading.css';

function SakuraLoading({ message = '正在连接服务器...' }: LoadingAnimationProps) {
  return (
    <div className="loading-screen">
      <div className="loading-backdrop" />

      <div className="loading-content">
        <div className="sakura-loader">
          <div className="sakura-petal-loader sakura-1">
            <svg width="40" height="40" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffb3d9"
                opacity="0.9"
              />
            </svg>
          </div>
          <div className="sakura-petal-loader sakura-2">
            <svg width="40" height="40" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffc0cb"
                opacity="0.8"
              />
            </svg>
          </div>
          <div className="sakura-petal-loader sakura-3">
            <svg width="40" height="40" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ff99cc"
                opacity="0.85"
              />
            </svg>
          </div>
        </div>

        <p className="loading-text">{message}</p>

        <div className="loading-dots">
          <span className="dot dot-1">.</span>
          <span className="dot dot-2">.</span>
          <span className="dot dot-3">.</span>
        </div>
      </div>
    </div>
  );
}

export default SakuraLoading;
