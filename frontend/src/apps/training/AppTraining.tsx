import { FeedbackProvider, TrainingFlowProvider } from '@/contexts';
import TrainingRouter from '@/router/trainingRouter';

function AppTraining() {
  return (
    <FeedbackProvider>
      <TrainingFlowProvider>
        <TrainingRouter />
      </TrainingFlowProvider>
    </FeedbackProvider>
  );
}

export default AppTraining;
