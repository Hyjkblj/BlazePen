import { createContext } from 'react';
import type { TrainingMode, TrainingRuntimeState } from '@/types/training';

export interface ActiveTrainingSessionState {
  sessionId: string;
  trainingMode: TrainingMode;
  characterId: string | null;
  status: string;
  roundNo: number;
  totalRounds: number | null;
  runtimeState: TrainingRuntimeState;
}

export interface TrainingFlowState {
  activeSession: ActiveTrainingSessionState | null;
}

export interface SetActiveTrainingSessionParams {
  sessionId: string;
  trainingMode: TrainingMode;
  characterId?: string | null;
  status: string;
  roundNo: number;
  totalRounds?: number | null;
  runtimeState: TrainingRuntimeState;
}

export interface SyncTrainingSessionProgressParams {
  sessionId: string;
  status: string;
  roundNo: number;
  totalRounds: number;
  runtimeState: TrainingRuntimeState;
}

export interface TrainingFlowContextValue {
  state: TrainingFlowState;
  setActiveSession: (params: SetActiveTrainingSessionParams) => void;
  clearActiveSession: () => void;
  syncProgress: (params: SyncTrainingSessionProgressParams) => void;
}

export const createTrainingFlowState = (): TrainingFlowState => ({
  activeSession: null,
});

export const buildActiveTrainingSession = ({
  sessionId,
  trainingMode,
  characterId = null,
  status,
  roundNo,
  totalRounds = null,
  runtimeState,
}: SetActiveTrainingSessionParams): ActiveTrainingSessionState => ({
  sessionId,
  trainingMode,
  characterId,
  status,
  roundNo,
  totalRounds,
  runtimeState,
});

export const TrainingFlowContext = createContext<TrainingFlowContextValue | null>(null);
