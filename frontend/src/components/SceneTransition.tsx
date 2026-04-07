import React, { useEffect, useState } from 'react';
import './SceneTransition.css';

export type SceneTransitionTone = 'story' | 'training';

interface SceneTransitionProps {
  sceneName: string;
  // Kept for API compatibility with existing call sites.
  actNumber: number;
  onComplete: () => void;
  tone?: SceneTransitionTone;
  bridgeSummary?: string | null;
}

const SceneTransition: React.FC<SceneTransitionProps> = ({
  sceneName,
  onComplete,
  tone = 'story',
  bridgeSummary,
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [showContent, setShowContent] = useState(false);

  useEffect(() => {
    const contentTimer = setTimeout(() => {
      setShowContent(true);
    }, 300);

    const completeTimer = setTimeout(() => {
      setIsVisible(false);
      onComplete();
    }, 2500);

    return () => {
      clearTimeout(contentTimer);
      clearTimeout(completeTimer);
    };
  }, [onComplete]);

  if (!isVisible) return null;

  return (
    <div
      className={`scene-transition-overlay${tone === 'training' ? ' scene-transition-overlay--training' : ''}`}
    >
      <div className="scene-transition-container">
        {tone === 'training' ? (
          <div className={`scene-transition-eyebrow ${showContent ? 'show' : ''}`}>实训 · 大场景</div>
        ) : null}

        <div className={`scene-name ${showContent ? 'show' : ''}`}>
          {sceneName}
        </div>

        {bridgeSummary ? (
          <p className={`scene-transition-bridge ${showContent ? 'show' : ''}`}>
            {bridgeSummary}
          </p>
        ) : null}

        <div className={`decoration-line ${showContent ? 'show' : ''}`} />
      </div>
    </div>
  );
};

export default SceneTransition;
