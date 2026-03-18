import { useContext } from 'react';
import { GameFlowContext } from './gameFlowCore';

export function useGameFlow() {
  const context = useContext(GameFlowContext);
  if (!context) {
    throw new Error('useGameFlow must be used within GameFlowProvider.');
  }
  return context;
}
