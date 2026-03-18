import AppRouter from './router';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import './App.css';

function App() {
  return (
    <FeedbackProvider>
      <GameFlowProvider>
        <AppRouter />
      </GameFlowProvider>
    </FeedbackProvider>
  );
}

export default App;
