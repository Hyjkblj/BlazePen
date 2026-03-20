import { useTrainingFlow } from '@/contexts';
import type { ActiveTrainingSessionState } from '@/contexts';

const TRAINING_MODE_LABELS = {
  guided: '引导训练',
  'self-paced': '自主训练',
  adaptive: '自适应训练',
} as const;

export interface UseTrainingSessionFlowResult {
  activeSession: ActiveTrainingSessionState | null;
  hasActiveSession: boolean;
  trainingModeLabel: string | null;
  clearTrainingSession: () => void;
}

export function useTrainingSessionFlow(): UseTrainingSessionFlowResult {
  const { state, clearActiveSession } = useTrainingFlow();
  const activeSession = state.activeSession;

  return {
    activeSession,
    hasActiveSession: activeSession !== null,
    trainingModeLabel: activeSession ? TRAINING_MODE_LABELS[activeSession.trainingMode] : null,
    clearTrainingSession: clearActiveSession,
  };
}
