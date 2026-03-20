import AppRouter from './router';
import { FeedbackProvider, GameFlowProvider, TrainingFlowProvider } from '@/contexts';
import './App.css';

function App() {
  return (
    <FeedbackProvider>
      <GameFlowProvider>
        <TrainingFlowProvider>
          <AppRouter />
        </TrainingFlowProvider>
      </GameFlowProvider>
    </FeedbackProvider>
  );
}

export default App;
