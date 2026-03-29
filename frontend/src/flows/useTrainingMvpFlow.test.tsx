// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTrainingMvpFlow } from './useTrainingMvpFlow';

const hookMocks = vi.hoisted(() => ({
  bootstrap: {
    status: 'idle',
    errorMessage: null,
    hasResumeTarget: false,
    resumeTarget: null,
    activeSession: null,
    restoreSession: vi.fn(),
    startTrainingSession: vi.fn(),
    dismissError: vi.fn(),
    clearTrainingSession: vi.fn(),
  },
  roundRunner: {
    status: 'idle',
    errorMessage: null,
    dismissError: vi.fn(),
    submitRound: vi.fn(),
  },
  sessionViewModel: {
    resolveRestoreIdentity: vi.fn(),
    autoRestoreSessionId: null,
    preferredTrainingMode: null,
    preferredCharacterId: null as string | null,
    currentSessionId: null,
  },
}));

const sessionViewBuilders = vi.hoisted(() => ({
  buildBlockedTrainingSessionView: vi.fn(),
  buildCompletedTrainingSessionView: vi.fn(),
  buildTrainingSessionViewFromInit: vi.fn(),
  buildTrainingSessionViewFromNext: vi.fn(),
  buildTrainingSessionViewFromSummary: vi.fn(),
}));

const telemetryMocks = vi.hoisted(() => ({
  trackFrontendTelemetry: vi.fn(),
}));

const trainingApiMocks = vi.hoisted(() => ({
  createTrainingMediaTask: vi.fn(),
  getTrainingMediaTask: vi.fn(),
  getTrainingReport: vi.fn(),
}));

vi.mock('@/hooks/useTrainingSessionBootstrap', () => ({
  useTrainingSessionBootstrap: () => hookMocks.bootstrap,
}));

vi.mock('@/hooks/useTrainingRoundRunner', () => ({
  useTrainingRoundRunner: () => hookMocks.roundRunner,
}));

vi.mock('@/hooks/useTrainingSessionViewModel', () => ({
  useTrainingSessionViewModel: () => hookMocks.sessionViewModel,
  ...sessionViewBuilders,
}));

vi.mock('@/services/frontendTelemetry', () => telemetryMocks);

vi.mock('@/services/trainingApi', () => trainingApiMocks);

const createScenario = (id: string, title: string) => ({
  id,
  title,
  eraDate: '1941-06-14',
  location: 'Shanghai',
  brief: `${title} brief`,
  mission: 'Protect the source while filing the story.',
  decisionFocus: 'Choose the safest next move.',
  targetSkills: ['verification'],
  riskTags: ['exposure'],
  options: [
    {
      id: `${id}-opt-1`,
      label: 'Hold publication',
      impactHint: 'Protect source safety',
    },
  ],
  completionHint: '',
  recommendation: null,
});

const createSessionView = (scenarioId: string, scenarioTitle: string) => ({
  sessionId: 'training-session-1',
  characterId: 42,
  status: 'in_progress',
  trainingMode: 'guided',
  roundNo: 0,
  totalRounds: 6,
  isCompleted: false,
  runtimeState: {
    currentRoundNo: 0,
    currentSceneId: scenarioId,
    kState: { K1: 0.45 },
    sState: { source_safety: 0.88 },
    runtimeFlags: {
      panicTriggered: false,
      sourceExposed: false,
      editorLocked: false,
      highRiskPath: false,
    },
    stateBar: {
      editorTrust: 0.7,
      publicStability: 0.8,
      sourceSafety: 0.88,
    },
    playerProfile: null,
  },
  currentScenario: createScenario(scenarioId, scenarioTitle),
  scenarioCandidates: [],
  progressAnchor: {
    roundNo: 0,
    totalRounds: 6,
    completedRounds: 0,
    remainingRounds: 6,
    progressPercent: 0,
    nextRoundNo: 1,
  },
  canResume: true,
  createdAt: null,
  updatedAt: null,
  endTime: null,
});

describe('useTrainingMvpFlow', () => {
  beforeEach(() => {
    hookMocks.bootstrap.status = 'idle';
    hookMocks.bootstrap.errorMessage = null;
    hookMocks.bootstrap.hasResumeTarget = false;
    hookMocks.bootstrap.resumeTarget = null;
    hookMocks.bootstrap.activeSession = null;
    hookMocks.bootstrap.restoreSession.mockReset();
    hookMocks.bootstrap.startTrainingSession.mockReset();
    hookMocks.bootstrap.dismissError.mockReset();
    hookMocks.bootstrap.clearTrainingSession.mockReset();

    hookMocks.roundRunner.status = 'idle';
    hookMocks.roundRunner.errorMessage = null;
    hookMocks.roundRunner.dismissError.mockReset();
    hookMocks.roundRunner.submitRound.mockReset();

    hookMocks.sessionViewModel.resolveRestoreIdentity.mockReset();
    hookMocks.sessionViewModel.resolveRestoreIdentity.mockImplementation((sessionId?: string | null) => ({
      sessionId: sessionId ?? 'training-session-1',
      source: 'manual',
    }));
    hookMocks.sessionViewModel.autoRestoreSessionId = null;
    hookMocks.sessionViewModel.preferredTrainingMode = null;
    hookMocks.sessionViewModel.preferredCharacterId = null;
    hookMocks.sessionViewModel.currentSessionId = null;

    sessionViewBuilders.buildBlockedTrainingSessionView.mockReset();
    sessionViewBuilders.buildCompletedTrainingSessionView.mockReset();
    sessionViewBuilders.buildTrainingSessionViewFromInit.mockReset();
    sessionViewBuilders.buildTrainingSessionViewFromNext.mockReset();
    sessionViewBuilders.buildTrainingSessionViewFromSummary.mockReset();

    telemetryMocks.trackFrontendTelemetry.mockReset();

    trainingApiMocks.createTrainingMediaTask.mockReset();
    trainingApiMocks.getTrainingMediaTask.mockReset();
    trainingApiMocks.getTrainingReport.mockReset();
  });

  it('invalidates stale characterId when profile fields change', () => {
    const { result } = renderHook(() => useTrainingMvpFlow());

    act(() => {
      result.current.updateFormDraft('characterId', '123');
    });
    expect(result.current.formDraft.characterId).toBe('123');

    act(() => {
      result.current.updateFormDraft('playerName', '王小明');
    });
    expect(result.current.formDraft.characterId).toBe('');
    expect(result.current.formDraft.playerName).toBe('王小明');

    act(() => {
      result.current.updateFormDraft('characterId', '456');
      result.current.updateFormDraft('portraitPresetId', 'correspondent-female');
    });
    expect(result.current.formDraft.characterId).toBe('');
    expect(result.current.formDraft.portraitPresetId).toBe('correspondent-female');
  });

  it('blocks training start when characterId is missing', async () => {
    const { result } = renderHook(() => useTrainingMvpFlow());

    let started = true;
    await act(async () => {
      started = await result.current.startTraining();
    });

    expect(started).toBe(false);
    expect(hookMocks.bootstrap.startTrainingSession).not.toHaveBeenCalled();
    expect(result.current.noticeMessage).toContain('请先生成并确认形象图');
  });

  it('ignores dirty preferredCharacterId when hydrating form draft', async () => {
    hookMocks.sessionViewModel.preferredCharacterId = 'dirty-character-ref';

    const { result } = renderHook(() => useTrainingMvpFlow());

    await waitFor(() => {
      expect(telemetryMocks.trackFrontendTelemetry).toHaveBeenCalledWith(
        expect.objectContaining({
          domain: 'training',
          event: 'training.form.hydration',
          status: 'failed',
        })
      );
    });
    expect(result.current.formDraft.portraitPresetId).toBe('');
    expect(result.current.formDraft.characterId).toBe('');
  });

  it('should not recreate scene image task on same-session same-scenario restore', async () => {
    const initialSessionView = createSessionView('scenario-1', 'Initial Briefing');
    const restoredSessionView = createSessionView('scenario-1', 'Initial Briefing');

    hookMocks.bootstrap.startTrainingSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: initialSessionView.runtimeState,
      nextScenario: initialSessionView.currentScenario,
      scenarioCandidates: [],
    });
    hookMocks.bootstrap.restoreSession.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      characterId: 42,
      trainingMode: 'guided',
      status: 'in_progress',
      roundNo: 0,
      totalRounds: 6,
      runtimeState: restoredSessionView.runtimeState,
      progressAnchor: restoredSessionView.progressAnchor,
      resumableScenario: restoredSessionView.currentScenario,
      scenarioCandidates: [],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: null,
      endTime: null,
    });
    hookMocks.sessionViewModel.currentSessionId = 'training-session-1';
    sessionViewBuilders.buildTrainingSessionViewFromInit.mockReturnValue(initialSessionView);
    sessionViewBuilders.buildTrainingSessionViewFromSummary.mockReturnValue(restoredSessionView);

    trainingApiMocks.createTrainingMediaTask.mockResolvedValue({
      taskId: 'scene-task-1',
      sessionId: 'training-session-1',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      result: {
        preview_url: '/static/images/training/scene_initial.png',
      },
      error: null,
      createdAt: '2026-03-29T00:00:00Z',
      updatedAt: '2026-03-29T00:00:01Z',
      startedAt: '2026-03-29T00:00:00Z',
      finishedAt: '2026-03-29T00:00:01Z',
    });

    const { result } = renderHook(() => useTrainingMvpFlow());

    act(() => {
      result.current.updateFormDraft('characterId', '42');
    });

    await act(async () => {
      await result.current.startTraining();
    });

    await waitFor(() => {
      expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(result.current.sceneImageUrl).toBe('/static/images/training/scene_initial.png');
    });

    await act(async () => {
      await result.current.retryRestore();
    });

    await waitFor(() => {
      expect(hookMocks.bootstrap.restoreSession).toHaveBeenCalled();
    });
    expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(result.current.sceneImageUrl).toBe('/static/images/training/scene_initial.png');
  });
});

