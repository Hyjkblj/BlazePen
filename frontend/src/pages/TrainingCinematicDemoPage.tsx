import { useEffect, useState } from 'react';
import './TrainingCinematicDemoPage.css';

function TrainingCinematicDemoPage() {
  const [showContinueHint, setShowContinueHint] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setShowContinueHint(true);
    }, 2200);

    return () => {
      window.clearTimeout(timer);
    };
  }, []);

  return (
    <main className="training-cinematic-demo">
      <div className="training-cinematic-demo__grain" aria-hidden="true" />
      <div className="training-cinematic-demo__center">
        <p className="training-cinematic-demo__eyebrow">指挥频道已接入</p>
        <h1 className="training-cinematic-demo__title" data-text="你的代号是黄蜂">
          你的代号是黄蜂
        </h1>
      </div>
      <p
        className={`training-cinematic-demo__hint${
          showContinueHint ? ' training-cinematic-demo__hint--visible' : ''
        }`}
      >
        点击任意位置继续
      </p>
    </main>
  );
}

export default TrainingCinematicDemoPage;
