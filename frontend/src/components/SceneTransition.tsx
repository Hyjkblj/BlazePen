import React, { useEffect, useState } from 'react';
import './SceneTransition.css';

interface SceneTransitionProps {
  sceneName: string;
  actNumber: number;
  onComplete: () => void;
}

const SceneTransition: React.FC<SceneTransitionProps> = ({ sceneName, actNumber, onComplete }) => {
  const [isVisible, setIsVisible] = useState(true);
  const [showContent, setShowContent] = useState(false);

  useEffect(() => {
    // 延迟显示内容，让转场动画先开始
    const contentTimer = setTimeout(() => {
      setShowContent(true);
    }, 300);

    // 动画完成后调用回调
    const completeTimer = setTimeout(() => {
      setIsVisible(false);
      onComplete();
    }, 2500); // 总动画时长2.5秒

    return () => {
      clearTimeout(contentTimer);
      clearTimeout(completeTimer);
    };
  }, [onComplete]);

  if (!isVisible) return null;

  return (
    <div className="scene-transition-overlay">
      <div className="scene-transition-container">
        {/* 幕数显示 */}
        <div className={`act-number ${showContent ? 'show' : ''}`}>
          {actNumber === 1 ? '第一幕' : `第${actNumber}幕`}
        </div>
        
        {/* 场景名称 */}
        <div className={`scene-name ${showContent ? 'show' : ''}`}>
          {sceneName}
        </div>

        {/* 装饰线条 */}
        <div className={`decoration-line ${showContent ? 'show' : ''}`} />
      </div>
    </div>
  );
};

export default SceneTransition;
