import { useCallback, useState } from 'react';
import { useTrainingFlow } from '@/contexts';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { getNextTrainingScenario, submitTrainingRound } from '@/services/trainingApi';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import { persistTrainingResumeTarget } from '@/storage/trainingSessionCache';
import type {
  TrainingMode,
  TrainingRoundSubmitParams,
  TrainingRoundSubmitResult,
  TrainingRuntimeState,
  TrainingScenarioNextResult,
  TrainingSessionSummaryResult,
} from '@/types/training';

export type TrainingRoundRunnerStatus = 'idle' | 'submitting' | 'error';
export type TrainingRoundRecoveryReason =
  | 'duplicate'
  | 'completed'
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

const SESSION_LEVEL_RECOVERY_CODES = new Set([
  'TRAINING_ROUND_DUPLICATE',
  'TRAINING_SESSION_COMPLETED',
  'TRAINING_SESSION_NOT_FOUND',
  'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
]);

const getSubmitErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '提交训练回合超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练提交服务暂时不可用，请稍后重试。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '训练会话不存在，请重新开始训练。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '训练会话恢复状态损坏，请重新开始训练。';
  }

  return getServiceErrorMessage(error, '提交训练回合失败。');
};

const getNextScenarioErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '回合已提交，但下一训练场景加载超时，请重试恢复当前训练。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '回合已提交，但下一训练场景暂时不可用，请重试恢复当前训练。';
  }

  return getServiceErrorMessage(error, '回合已提交，但无法继续加载下一训练场景。');
};

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
          setErrorMessage(getNextScenarioErrorMessage(nextError));
          setStatus('error');
          return {
            submitResult,
            nextScenarioResult: null,
            summaryResult: null,
            recoveryReason: 'next-fetch-failed',
          };
        }
      } catch (error: unknown) {
        if (isServiceError(error) && SESSION_LEVEL_RECOVERY_CODES.has(error.code)) {
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
                recoveryReason:
                  error.code === 'TRAINING_ROUND_DUPLICATE' ? 'duplicate' : 'completed',
              },
            });
            return {
              submitResult: null,
              nextScenarioResult: null,
              summaryResult,
              recoveryReason:
                error.code === 'TRAINING_ROUND_DUPLICATE' ? 'duplicate' : 'completed',
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
        setErrorMessage(getSubmitErrorMessage(error));
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
