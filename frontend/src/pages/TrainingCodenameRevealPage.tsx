import { useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import TrainingCodenameReveal from '@/components/training/TrainingCodenameReveal';
import { ROUTES } from '@/config/routes';
import './TrainingCodenameRevealPage.css';

type TrainingCodenameRevealRouteState = {
  codename?: unknown;
};

const resolveCodenameFromRouteState = (state: unknown): string => {
  if (!state || typeof state !== 'object') {
    return '黄蜂';
  }
  const codename = (state as TrainingCodenameRevealRouteState).codename;
  const normalized = typeof codename === 'string' ? codename.trim() : '';
  return normalized || '黄蜂';
};

function TrainingCodenameRevealPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const codename = useMemo(() => resolveCodenameFromRouteState(location.state), [location.state]);

  const handleComplete = useCallback(() => {
    navigate(ROUTES.TRAINING_NEWSROOM_INTRO, { replace: true });
  }, [navigate]);

  return (
    <div className="training-codename-reveal-page">
      <TrainingCodenameReveal
        open
        codename={codename}
        onComplete={handleComplete}
      />
    </div>
  );
}

export default TrainingCodenameRevealPage;
