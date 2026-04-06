import { useState } from 'react';
import './TrainingCinematicDemoPage.css';

function TrainingCinematicDemoPage() {
  const [replayToken, setReplayToken] = useState(0);

  return (
    <main className="training-ribbon-demo">
      <div className="training-ribbon-demo__stage">
        <div
          key={replayToken}
          className="training-ribbon-demo__strip"
          role="img"
          aria-label="训练章节流光样式演示"
        >
          <div className="training-ribbon-demo__ambient" aria-hidden="true" />
          <svg
            className="training-ribbon-demo__lines"
            viewBox="0 0 1200 120"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              className="training-ribbon-demo__line training-ribbon-demo__line--a training-ribbon-demo__line--silver"
              d="M -120 42 C 80 92, 220 18, 430 62 C 620 92, 780 22, 960 58 C 1060 74, 1130 36, 1240 36"
            />
            <path
              className="training-ribbon-demo__line training-ribbon-demo__line--b training-ribbon-demo__line--black"
              d="M -120 70 C 70 16, 220 96, 390 56 C 560 18, 760 94, 940 54 C 1040 36, 1130 46, 1240 60"
            />
            <path
              className="training-ribbon-demo__line training-ribbon-demo__line--c training-ribbon-demo__line--silver"
              d="M -120 86 C 120 42, 300 90, 500 48 C 700 20, 900 82, 1080 48 C 1140 40, 1190 44, 1240 54"
            />
          </svg>
          <div className="training-ribbon-demo__flare" aria-hidden="true" />
          <p className="training-ribbon-demo__label" data-text="全部章节">
            全部章节
          </p>
        </div>

        <button
          type="button"
          className="training-ribbon-demo__replay"
          onClick={() => setReplayToken((value) => value + 1)}
        >
          重播动画
        </button>
      </div>
    </main>
  );
}

export default TrainingCinematicDemoPage;
