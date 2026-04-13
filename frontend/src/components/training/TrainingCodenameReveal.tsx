import { useMemo } from 'react';
import './TrainingCodenameReveal.css';

type TrainingCodenameRevealProps = {
  open: boolean;
  codename: string;
  onComplete: () => void;
};

function TrainingCodenameReveal({
  open,
  codename,
  onComplete,
}: TrainingCodenameRevealProps) {
  const normalizedCodename = useMemo(() => {
    const text = String(codename || '').trim();
    return text || '黄蜂';
  }, [codename]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="training-codename-reveal"
      role="button"
      tabIndex={0}
      aria-label="代号揭示动画，点击继续"
      onClick={onComplete}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onComplete();
        }
      }}
    >
      <div className="training-codename-reveal__bg" aria-hidden="true" />
      <p className="training-codename-reveal__subtitle">指挥频道已接入</p>
      <h2 className="training-codename-reveal__title">你的代号是{normalizedCodename}</h2>
      <p className="training-codename-reveal__hint">点击任意位置继续</p>
    </div>
  );
}

export default TrainingCodenameReveal;
