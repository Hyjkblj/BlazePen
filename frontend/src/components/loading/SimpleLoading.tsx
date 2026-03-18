import type { LoadingAnimationProps } from './types';
import './SimpleLoading.css';

function SimpleLoading({ message = '正在加载...' }: LoadingAnimationProps) {
  return (
    <div className="simple-loading-screen">
      <div className="simple-loading-backdrop" />
      <div className="simple-loading-content">
        <div className="simple-loading-spinner" aria-hidden="true" />
        <p className="simple-loading-text">{message}</p>
      </div>
    </div>
  );
}

export default SimpleLoading;
