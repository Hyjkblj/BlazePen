import { useReducer, type ReactNode } from 'react';
import {
  buildActiveTrainingSession,
  createTrainingFlowState,
  TrainingFlowContext,
  type ActiveTrainingSessionState,
  type SetActiveTrainingSessionParams,
  type SyncTrainingSessionProgressParams,
  type TrainingFlowState,
} from './trainingFlowCore';

type TrainingFlowAction =
  | { type: 'set-active-session'; payload: ActiveTrainingSessionState }
  | { type: 'clear-active-session' }
  | { type: 'sync-progress'; payload: SyncTrainingSessionProgressParams };

const reducer = (state: TrainingFlowState, action: TrainingFlowAction): TrainingFlowState => {
  switch (action.type) {
    case 'set-active-session':
      return {
        ...state,
        activeSession: action.payload,
      };
    case 'clear-active-session':
      return {
        ...state,
        activeSession: null,
      };
    case 'sync-progress':
      if (!state.activeSession || state.activeSession.sessionId !== action.payload.sessionId) {
        return state;
      }

      return {
        ...state,
        activeSession: {
          ...state.activeSession,
          status: action.payload.status,
          roundNo: action.payload.roundNo,
          totalRounds: action.payload.totalRounds,
          runtimeState: action.payload.runtimeState,
        },
      };
    default:
      return state;
  }
};

export function TrainingFlowProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, createTrainingFlowState());

  const setActiveSession = (params: SetActiveTrainingSessionParams) => {
    dispatch({
      type: 'set-active-session',
      payload: buildActiveTrainingSession(params),
    });
  };

  const clearActiveSession = () => {
    dispatch({ type: 'clear-active-session' });
  };

  const syncProgress = (params: SyncTrainingSessionProgressParams) => {
    dispatch({
      type: 'sync-progress',
      payload: params,
    });
  };

  return (
    <TrainingFlowContext.Provider
      value={{
        state,
        setActiveSession,
        clearActiveSession,
        syncProgress,
      }}
    >
      {children}
    </TrainingFlowContext.Provider>
  );
}
