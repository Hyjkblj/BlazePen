import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import TrainingMainHome from '@/components/training/TrainingMainHome';
import { ROUTES } from '@/config/routes';
import { useTrainingSessionBootstrap } from '@/hooks/useTrainingSessionBootstrap';

const DEFAULT_TRAINING_USER_ID = 'frontend-training-user';

function TrainingMainHomePage() {
  const navigate = useNavigate();
  const { startTrainingSession, status } = useTrainingSessionBootstrap();
  const [enterBusy, setEnterBusy] = useState(false);
  const enterDisabled = status === 'starting' || enterBusy;

  return (
    <TrainingMainHome
      enterDisabled={enterDisabled}
      onEnter={async () => {
        if (enterBusy || status === 'starting') {
          return;
        }
        setEnterBusy(true);
        try {
          const result = await startTrainingSession({
            userId: DEFAULT_TRAINING_USER_ID,
            trainingMode: 'guided',
            persistScenarioPrewarmPlan: true,
          });
          if (result) {
            navigate(ROUTES.TRAINING_LANDING);
          }
        } finally {
          setEnterBusy(false);
        }
      }}
    />
  );
}

export default TrainingMainHomePage;
