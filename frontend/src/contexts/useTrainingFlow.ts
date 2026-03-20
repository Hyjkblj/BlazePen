import { useContext } from 'react';
import { TrainingFlowContext } from './trainingFlowCore';

export function useTrainingFlow() {
  const context = useContext(TrainingFlowContext);
  if (!context) {
    throw new Error('useTrainingFlow must be used within TrainingFlowProvider.');
  }
  return context;
}
