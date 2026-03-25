import { useCallback, useState } from 'react';
import { useTrainingFlow } from '@/contexts';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { getNextTrainingScenario, submitTrainingRound } from '@/services/trainingApi';
import { persistTrainingResumeTarget } from '@/storage/trainingSessionCache';
import type {
  TrainingMode,
  TrainingRoundSubmitParams,
  TrainingRoundSubmitResult,
  TrainingRuntimeState,
  TrainingScenarioNextResult,
  TrainingSessionSummaryResult,
} from '@/types/training';
import {
  getTrainingRoundNextScenarioErrorMessage,
  getTrainingRoundSubmitErrorMessage,
  isTrainingRoundSessionLevelRecoveryError,
  resolveTrainingRoundRecoveryReason,
} from './trainingRoundRunnerExecutor';

export type TrainingRoundRunnerStatus = 'idle' | 'submitting' | 'error';
export type TrainingRoundRecoveryReason =
  | 'duplicate'
  | 'completed'
  | 'scenario-mismatch'
  | 'next-fetch-failed'
  | null;

export interface RestoreTrainingSessionDelegate {
  sessionId?: string | null;
  trainingMode?: TrainingMode | null;
  characterId?: string | null;
}

export interface TrainingRoundTransition {
  submitResult: TrainingRoundSubmitResult | null;
  nextScenarioResult: TrainingScenarioNextResult | null;
  summaryResult: TrainingSessionSummaryResult | null;
  recoveryReason: TrainingRoundRecoveryReason;
}

export interface UseTrainingRoundRunnerOptions {
  restoreSession: (
    options?: RestoreTrainingSessionDelegate
  ) => Promise<TrainingSessionSummaryResult | null>;
}

export interface UseTrainingRoundRunnerResult {
  status: TrainingRoundRunnerStatus;
  errorMessage: string | null;
  submitRound: (
    params: Omit<TrainingRoundSubmitParams, 'sessionId'>
  ) => Promise<TrainingRoundTransition | null>;
  dismissError: () => void;
}

export function useTrainingRoundRunner({
  restoreSession,
}: UseTrainingRoundRunnerOptions): UseTrainingRoundRunnerResult {
  const { state, setActiveSession } = useTrainingFlow();
  const [status, setStatus] = useState<TrainingRoundRunnerStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const dismissError = useCallback(() => {
    setErrorMessage(null);
    if (status === 'error') {
      setStatus('idle');
    }
  }, [status]);

  const syncSession = useCallback(
    (nextStatus: string, roundNo: number, runtimeState: TrainingRuntimeState) => {
      const activeSession = state.activeSession;
      if (!activeSession) {
        return;
      }

      setActiveSession({
        sessionId: activeSession.sessionId,
        trainingMode: activeSession.trainingMode,
        characterId: activeSession.characterId,
        status: nextStatus,
        roundNo,
        totalRounds: activeSession.totalRounds,
        runtimeState,
      });
      persistTrainingResumeTarget({
        sessionId: activeSession.sessionId,
        trainingMode: activeSession.trainingMode,
        characterId: activeSession.characterId,
        status: nextStatus,
      });
    },
    [setActiveSession, state.activeSession]
  );

  const restoreCurrentSession = useCallback(async () => {
    const activeSession = state.activeSession;
    return restoreSession({
      sessionId: activeSession?.sessionId ?? null,
      trainingMode: activeSession?.trainingMode ?? null,
      characterId: activeSession?.characterId ?? null,
    });
  }, [restoreSession, state.activeSession]);

  const submitRound = useCallback(
    async (
      params: Omit<TrainingRoundSubmitParams, 'sessionId'>
    ): Promise<TrainingRoundTransition | null> => {
      const activeSession = state.activeSession;
      const submitTelemetryMetadata = {
        sessionId: activeSession?.sessionId ?? null,
        scenarioId: params.scenarioId,
        selectedOptionId: params.selectedOption ?? null,
        hasUserInput: params.userInput.trim() !== '',
      };
      if (!activeSession?.sessionId) {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.round.submit',
          status: 'failed',
          metadata: {
            ...submitTelemetryMetadata,
            failureStage: 'missing-session',
          },
        });
        setErrorMessage('当前没有可提交的训练会话。');
        setStatus('error');
        return null;
      }

      setStatus('submitting');
      setErrorMessage(null);

      try {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.round.submit',
          status: 'requested',
          metadata: submitTelemetryMetadata,
        });
        const submitResult = await submitTrainingRound({
          sessionId: activeSession.sessionId,
          scenarioId: params.scenarioId,
          userInput: params.userInput,
          selectedOption: params.selectedOption,
          ...(Array.isArray(params.mediaTasks) && params.mediaTasks.length > 0
            ? { mediaTasks: params.mediaTasks }
            : {}),
        });

        syncSession(
          submitResult.isCompleted ? 'completed' : 'in_progress',
          submitResult.roundNo,
          submitResult.runtimeState
        );

        if (submitResult.isCompleted) {
          setStatus('idle');
          trackFrontendTelemetry({
            domain: 'training',
            event: 'training.round.submit',
            status: 'succeeded',
            metadata: {
              ...submitTelemetryMetadata,
              roundNo: submitResult.roundNo,
              status: 'completed',
              isCompleted: true,
              recoveryReason: null,
            },
          });
          return {
            submitResult,
            nextScenarioResult: null,
            summaryResult: null,
            recoveryReason: null,
          };
        }

        try {
          const nextScenarioResult = await getNextTrainingScenario({
            sessionId: activeSession.sessionId,
          });
          syncSession(
            nextScenarioResult.status,
            nextScenarioResult.roundNo,
            nextScenarioResult.runtimeState
          );
          setStatus('idle');
          trackFrontendTelemetry({
            domain: 'training',
            event: 'training.round.submit',
            status: 'succeeded',
            metadata: {
              ...submitTelemetryMetadata,
              roundNo: nextScenarioResult.roundNo,
              status: nextScenarioResult.status,
              isCompleted: false,
              recoveryReason: null,
            },
          });
          return {
            submitResult,
            nextScenarioResult,
            summaryResult: null,
            recoveryReason: null,
          };
        } catch (nextError: unknown) {
          const summaryResult = await restoreCurrentSession();
          if (summaryResult) {
            setStatus('idle');
            trackFrontendTelemetry({
              domain: 'training',
              event: 'training.round.submit',
              status: 'succeeded',
              metadata: {
                ...submitTelemetryMetadata,
                roundNo: summaryResult.roundNo,
                status: summaryResult.status,
                isCompleted: summaryResult.isCompleted,
                recoveryReason: 'next-fetch-failed',
              },
            });
            return {
              submitResult,
              nextScenarioResult: null,
              summaryResult,
              recoveryReason: 'next-fetch-failed',
            };
          }

          trackFrontendTelemetry({
            domain: 'training',
            event: 'training.round.submit',
            status: 'failed',
            metadata: {
              ...submitTelemetryMetadata,
              failureStage: 'next-scenario',
            },
            cause: nextError,
          });
          setErrorMessage(getTrainingRoundNextScenarioErrorMessage(nextError));
          setStatus('error');
          return {
            submitResult,
            nextScenarioResult: null,
            summaryResult: null,
            recoveryReason: 'next-fetch-failed',
          };
        }
      } catch (error: unknown) {
        if (isTrainingRoundSessionLevelRecoveryError(error)) {
          const summaryResult = await restoreCurrentSession();
          if (summaryResult) {
            const recoveryReason = resolveTrainingRoundRecoveryReason(error);
            setStatus('idle');
            trackFrontendTelemetry({
              domain: 'training',
              event: 'training.round.submit',
              status: 'succeeded',
              metadata: {
                ...submitTelemetryMetadata,
                roundNo: summaryResult.roundNo,
                status: summaryResult.status,
                isCompleted: summaryResult.isCompleted,
                recoveryReason,
              },
            });
            return {
              submitResult: null,
              nextScenarioResult: null,
              summaryResult,
              recoveryReason,
            };
          }
        }

        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.round.submit',
          status: 'failed',
          metadata: {
            ...submitTelemetryMetadata,
            failureStage: 'submit',
          },
          cause: error,
        });
        setErrorMessage(getTrainingRoundSubmitErrorMessage(error));
        setStatus('error');
        return null;
      }
    },
    [restoreCurrentSession, state.activeSession, syncSession]
  );

  return {
    status,
    errorMessage,
    submitRound,
    dismissError,
  };
}
