import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import warIntroVideo from '@/assets/video/war-intro-seedance-1-5-pro.mp4';
import './TrainingCinematicDemoPage.css';

function TrainingCinematicDemoPage() {
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [manualStartRequired, setManualStartRequired] = useState(false);

  const handleEnded = useCallback(() => {
    navigate(ROUTES.TRAINING, { replace: true });
  }, [navigate]);

  useEffect(() => {
    if (import.meta.env.MODE === 'test') {
      return;
    }
    const video = videoRef.current;
    if (!video) {
      return;
    }
    void video
      .play()
      .then(() => {
        setManualStartRequired(false);
      })
      .catch(() => {
        setManualStartRequired(true);
      });
  }, []);

  const handleManualStart = useCallback(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    void video
      .play()
      .then(() => {
        setManualStartRequired(false);
      })
      .catch(() => {
        setManualStartRequired(true);
      });
  }, []);

  return (
    <div
      className="training-cinematic-video"
      role={manualStartRequired ? 'button' : undefined}
      tabIndex={manualStartRequired ? 0 : undefined}
      aria-label={manualStartRequired ? '点击播放开场视频' : undefined}
      onClick={manualStartRequired ? handleManualStart : undefined}
      onKeyDown={
        manualStartRequired
          ? (event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleManualStart();
              }
            }
          : undefined
      }
    >
      <video
        ref={videoRef}
        className="training-cinematic-video__video"
        src={warIntroVideo}
        preload="auto"
        playsInline
        autoPlay
        onEnded={handleEnded}
      />
      {manualStartRequired ? (
        <div className="training-cinematic-video__hint">点击任意位置播放开场视频</div>
      ) : null}
    </div>
  );
}

export default TrainingCinematicDemoPage;
