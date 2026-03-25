import { useNavigate } from 'react-router-dom';
import TrainingMainHome from '@/components/training/TrainingMainHome';
import { ROUTES } from '@/config/routes';

function TrainingMainHomePage() {
  const navigate = useNavigate();

  return (
    <TrainingMainHome
      onEnter={() => {
        navigate(ROUTES.TRAINING_LANDING);
      }}
    />
  );
}

export default TrainingMainHomePage;
