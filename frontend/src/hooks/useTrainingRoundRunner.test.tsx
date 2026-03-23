// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TrainingFlowProvider, useTrainingFlow } from '@/contexts';
import { ServiceError } from '@/services/serviceError';
import { readTrainingResumeTarget } from '@/storage/trainingSessionCache';
import type {
  TrainingRoundSubmitResult,
  TrainingRuntimeState,
  TrainingSessionSummaryResult,
} from '@/types/training';
import { useTrainingRoundRunner } from './useTrainingRoundRunner';

const trainingApiMocks = vi.hoisted(() => ({
  submitTrainingRound: vi.fn(),
  getNextTrainingScenario: vi.fn(),
}));

const telemetrySpy = vi.hoisted(() => vi.fn());

vi.mock('@/services/trainingApi', () => trainingApiMocks);

vi.mock('@/services/frontendTelemetry', () => ({
  trackFrontendTelemetry: telemetrySpy,
}));

const createRuntimeState = (sceneId: string, roundNo: number): TrainingRuntimeState => ({
  currentRoundNo: roundNo,
  currentSceneId: sceneId,
  kState: {
    K1: 0.45,
  },
  sState: {
    source_safety: 0.88,
  },
  runtimeFlags: {
    panicTriggered: false,
    sourceExposed: false,
    editorLocked: false,
    highRiskPath: false,
  },
  stateBar: {
    editorTrust: 0.72,
    publicStability: 0.81,
    sourceSafety: 0.88,
  },
  playerProfile: null,
});

const createSubmitResult = (
  overrides: Partial<TrainingRoundSubmitResult> = {}
): TrainingRoundSubmitResult => ({
  sessionId: 'training-session-active',
  roundNo: 1,
  runtimeState: createRuntimeState('scenario-1', 1),
  evaluation: {
    llmModel: 'rules_v1',
    confidence: 0.82,
    riskFlags: [],
    skillDelta: {},
    stateDelta: {},
    evidence: [],
    skillScoresPreview: {},
    evalMode: 'rules_only',
    fallbackReason: null,
    calibration: null,
    llmRawText: null,
  },
  consequenceEvents: [],
  isCompleted: false,
  ending: null,
  decisionContext: null,
  ...overrides,
});

const createSummaryResult = (
  overrides: Partial<TrainingSessionSummaryResult> = {}
): TrainingSessionSummaryResult => ({
  sessionId: 'training-session-active',
  characterId: 'character-42',
  trainingMode: 'guided',
  status: 'in_progress',
  roundNo: 1,
  totalRounds: 6,
  runtimeState: createRuntimeState('scenario-1', 1),
  progressAnchor: {
    roundNo: 1,
    totalRounds: 6,
    completedRounds: 1,
    remainingRounds: 5,
    progressPercent: 16.67,
    nextRoundNo: 2,
  },
  resumableScenario: null,
  scenarioCandidates: [],
  canResume: true,
  isCompleted: false,
  createdAt: null,
  updatedAt: null,
  endTime: null,
  ...overrides,
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <TrainingFlowProvider>{children}</TrainingFlowProvider>
);

const seedActiveSession = (
  setActiveSession: ReturnType<typeof useTrainingFlow>['setActiveSession']
) => {
  act(() => {
    setActiveSession({
      sessionId: 'training-session-active',
      trainingMode: 'guided',
      characterId: 'character-42',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-1', 1),
    });
  });
};

describe('useTrainingRoundRunner', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('restores the current session when submit is rejected as duplicate', async () => {
    trainingApiMocks.submitTrainingRound.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_ROUND_DUPLICATE',
        message: 'duplicate round submit',
      })
    );
    const restoreSession = vi
      .fn()
      .mockResolvedValueOnce(createSummaryResult({ roundNo: 2 }));

    const { result } = renderHook(
      () => ({
        runner: useTrainingRoundRunner({ restoreSession }),
        trainingFlow: useTrainingFlow(),
      }),
      { wrapper }
    );

    seedActiveSession(result.current.trainingFlow.setActiveSession);

    let transition: Awaited<ReturnType<typeof result.current.runner.submitRound>> = null;
    await act(async () => {
      transition = await result.current.runner.submitRound({
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: null,
      });
    });

    expect(restoreSession).toHaveBeenCalledWith({
      sessionId: 'training-session-active',
      trainingMode: 'guided',
      characterId: 'character-42',
    });
    expect(transition).toMatchObject({
      submitResult: null,
      nextScenarioResult: null,
      summaryResult: {
        sessionId: 'training-session-active',
        roundNo: 2,
      },
      recoveryReason: 'duplicate',
    });
    expect(result.current.runner.status).toBe('idle');
    expect(result.current.runner.errorMessage).toBeNull();
    expect(trainingApiMocks.getNextTrainingScenario).not.toHaveBeenCalled();
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.round.submit',
        status: 'succeeded',
        metadata: expect.objectContaining({
          recoveryReason: 'duplicate',
        }),
      })
    );
  });

  it.each([
    ['TRAINING_SESSION_COMPLETED', 'completed'],
    ['TRAINING_SESSION_NOT_FOUND', null],
    ['TRAINING_SESSION_RECOVERY_STATE_CORRUPTED', null],
  ] as const)(
    'restores the current session when submit hits session-level error %s',
    async (errorCode, expectedRecoveryReason) => {
      trainingApiMocks.submitTrainingRound.mockRejectedValueOnce(
        new ServiceError({
          code: errorCode,
          message: `${errorCode} during submit`,
        })
      );
      const restoreSession = vi.fn().mockResolvedValueOnce(
        createSummaryResult({
          status: 'completed',
          isCompleted: true,
          roundNo: 6,
        })
      );

      const { result } = renderHook(
        () => ({
          runner: useTrainingRoundRunner({ restoreSession }),
          trainingFlow: useTrainingFlow(),
        }),
        { wrapper }
      );

      seedActiveSession(result.current.trainingFlow.setActiveSession);

      let transition: Awaited<ReturnType<typeof result.current.runner.submitRound>> = null;
      await act(async () => {
        transition = await result.current.runner.submitRound({
          scenarioId: 'scenario-1',
          userInput: 'Protect source',
          selectedOption: null,
        });
      });

      expect(restoreSession).toHaveBeenCalledTimes(1);
      expect(transition).toMatchObject({
        submitResult: null,
        nextScenarioResult: null,
        summaryResult: {
          sessionId: 'training-session-active',
          status: 'completed',
          roundNo: 6,
        },
        recoveryReason: expectedRecoveryReason,
      });
      expect(result.current.runner.status).toBe('idle');
      expect(result.current.runner.errorMessage).toBeNull();
    }
  );

  it('uses stable completed message when session is already completed and restore fails', async () => {
    trainingApiMocks.submitTrainingRound.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SESSION_COMPLETED',
        message: 'session already completed',
      })
    );
    const restoreSession = vi.fn().mockResolvedValueOnce(null);

    const { result } = renderHook(
      () => ({
        runner: useTrainingRoundRunner({ restoreSession }),
        trainingFlow: useTrainingFlow(),
      }),
      { wrapper }
    );

    seedActiveSession(result.current.trainingFlow.setActiveSession);

    let transition: Awaited<ReturnType<typeof result.current.runner.submitRound>> = null;
    await act(async () => {
      transition = await result.current.runner.submitRound({
        scenarioId: 'scenario-1',
        userInput: 'Protect source',
        selectedOption: null,
      });
    });

    expect(restoreSession).toHaveBeenCalledTimes(1);
    expect(transition).toBeNull();
    expect(result.current.runner.status).toBe('error');
    expect(result.current.runner.errorMessage).toBe(
      '训练已完成，请查看训练报告或重新开始训练。'
    );
  });

  it('surfaces a stable error when next scenario loading fails and restore also fails', async () => {
    trainingApiMocks.submitTrainingRound.mockResolvedValueOnce(createSubmitResult());
    trainingApiMocks.getNextTrainingScenario.mockRejectedValueOnce(
      new ServiceError({
        code: 'REQUEST_TIMEOUT',
        message: 'next scenario timeout',
      })
    );
    const restoreSession = vi.fn().mockResolvedValueOnce(null);

    const { result } = renderHook(
      () => ({
        runner: useTrainingRoundRunner({ restoreSession }),
        trainingFlow: useTrainingFlow(),
      }),
      { wrapper }
    );

    seedActiveSession(result.current.trainingFlow.setActiveSession);

    let transition: Awaited<ReturnType<typeof result.current.runner.submitRound>> = null;
    await act(async () => {
      transition = await result.current.runner.submitRound({
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: null,
      });
    });

    expect(restoreSession).toHaveBeenCalledWith({
      sessionId: 'training-session-active',
      trainingMode: 'guided',
      characterId: 'character-42',
    });
    expect(transition).toMatchObject({
      submitResult: {
        sessionId: 'training-session-active',
        roundNo: 1,
      },
      nextScenarioResult: null,
      summaryResult: null,
      recoveryReason: 'next-fetch-failed',
    });
    expect(result.current.runner.status).toBe('error');
    expect(result.current.runner.errorMessage).toBe(
      '回合已提交，但下一训练场景加载超时，请重试恢复当前训练。'
    );
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-active',
      trainingMode: 'guided',
      characterId: 'character-42',
      status: 'in_progress',
    });
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'training',
        event: 'training.round.submit',
        status: 'failed',
        metadata: expect.objectContaining({
          failureStage: 'next-scenario',
        }),
      })
    );
  });
});
