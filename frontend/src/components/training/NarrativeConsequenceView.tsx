import { useEffect, useState } from 'react';
import '../../pages/Training.css';

interface NarrativeConsequenceViewProps {
  lines: string[];
  onClick: () => void;
}

function NarrativeConsequenceView({ lines, onClick }: NarrativeConsequenceViewProps) {
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    setVisibleCount(0);
    if (lines.length === 0) return;

    let current = 0;
    const showNext = () => {
      current += 1;
      setVisibleCount(current);
      if (current < lines.length) {
        timer = window.setTimeout(showNext, 600);
      }
    };

    let timer = window.setTimeout(showNext, 300);
    return () => window.clearTimeout(timer);
  }, [lines]);

  if (lines.length === 0) return null;

  return (
    <div
      className="training-consequence-view"
      role="region"
      aria-label="后果叙事"
      onClick={onClick}
    >
      <ul className="training-consequence-view__lines" aria-live="polite">
        {lines.map((line, index) => (
          <li
            key={index}
            className={`training-consequence-view__line${index < visibleCount ? ' training-consequence-view__line--visible' : ''}`}
          >
            {line}
          </li>
        ))}
      </ul>
      <p className="training-consequence-view__hint" aria-hidden="true">
        点击继续
      </p>
    </div>
  );
}

export default NarrativeConsequenceView;
