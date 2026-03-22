// @vitest-environment jsdom

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ROUTES,
  buildTrainingDiagnosticsRoute,
  buildTrainingProgressRoute,
  buildTrainingReportRoute,
} from '@/config/routes';
import {
  FeedbackProvider,
  TrainingFlowProvider,
  useTrainingFlow,
  type ActiveTrainingSessionState,
} from '@/contexts';
import { ServiceError } from '@/services/serviceError';
import Training from '@/pages/Training';
import {
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';

const trainingApiMocks = vi.hoisted(() => ({
  initTraining: vi.fn(),
  getTrainingSessionSummary: vi.fn(),
  submitTrainingRound: vi.fn(),
  getNextTrainingScenario: vi.fn(),
  getTrainingProgress: vi.fn(),
}));

vi.mock('@/services/trainingApi', () => trainingApiMocks);

const createRuntimeState = (sceneId: string, roundNo: number) => ({
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
    editorTrust: 0.7,
    publicStability: 0.8,
    sourceSafety: 0.88,
  },
  playerProfile: null,
});

const createScenario = (id: string, title: string, optionLabel = 'Hold publication') => ({
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
      label: optionLabel,
      impactHint: 'Protect source safety',
    },
  ],
  completionHint: '',
  recommendation: null,
});

function TrainingFlowSeed({
  activeSession,
  children,
}: {
  activeSession: ActiveTrainingSessionState | null;
  children: ReactNode;
}) {
  const { setActiveSession } = useTrainingFlow();
  const [isReady, setReady] = useState(activeSession === null);
  const initializedRef = useRef(activeSession === null);

  useLayoutEffect(() => {
    if (initializedRef.current) {
      return;
    }

    initializedRef.current = true;
    if (activeSession) {
      setActiveSession(activeSession);
    }

    setReady(true);
  }, [activeSession, setActiveSession]);

  return isReady ? <>{children}</> : null;
}

const renderRouterApp = (
  pathname: string,
  { activeSession = null }: { activeSession?: ActiveTrainingSessionState | null } = {}
) =>
  render(
    <FeedbackProvider>
      <TrainingFlowProvider>
        <TrainingFlowSeed activeSession={activeSession}>
          <MemoryRouter initialEntries={[pathname]}>
            <Routes>
              <Route path={ROUTES.TRAINING} element={<Training />} />
            </Routes>
          </MemoryRouter>
        </TrainingFlowSeed>
      </TrainingFlowProvider>
    </FeedbackProvider>
  );

const expectTrainingInsightLinks = (
  container: HTMLElement,
  sessionId: string
) => {
  const subnavLinks = Array.from(
    container.querySelectorAll<HTMLAnchorElement>('.training-shell__subnav-link')
  );

  expect(subnavLinks.map((link) => link.getAttribute('href'))).toEqual([
    buildTrainingProgressRoute(sessionId),
    buildTrainingReportRoute(sessionId),
    buildTrainingDiagnosticsRoute(sessionId),
  ]);
};

describe('Training route integration', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('starts a new training session and advances to the next scenario after round submission', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
    });
    trainingApiMocks.submitTrainingRound.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      roundNo: 1,
      runtimeState: createRuntimeState('scenario-1', 1),
      evaluation: {
        llmModel: 'rules_v1',
        confidence: 0.82,
        riskFlags: ['source_exposure'],
        skillDelta: {
          verification: 0.2,
        },
        stateDelta: {
          source_safety: 0.05,
        },
        evidence: ['confirmed timeline'],
        skillScoresPreview: {
          verification: 0.72,
        },
        evalMode: 'rules_only',
        fallbackReason: null,
        calibration: null,
        llmRawText: null,
      },
      consequenceEvents: [
        {
          eventType: 'source_warning',
          label: 'Source warning',
          summary: 'Source risk increased',
          severity: 'high',
          roundNo: 1,
          relatedFlag: null,
          stateBar: null,
          payload: {},
        },
      ],
      isCompleted: false,
      ending: null,
      decisionContext: {
        mode: 'guided',
        selectionSource: 'manual',
        selectedScenarioId: 'scenario-1',
        recommendedScenarioId: null,
        candidatePool: [],
        selectedRecommendation: null,
        recommendedRecommendation: null,
        selectedBranchTransition: null,
        recommendedBranchTransition: null,
      },
    });
    trainingApiMocks.getNextTrainingScenario.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      status: 'in_progress',
      roundNo: 1,
      runtimeState: createRuntimeState('scenario-2', 1),
      scenario: createScenario('scenario-2', 'Follow Up Interview', 'Delay publication'),
      scenarioCandidates: [],
      ending: null,
    });

    const { container } = renderRouterApp(ROUTES.TRAINING);

    expect(await screen.findByText('Training Frontend MVP')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '启动训练' }));

    await waitFor(() => {
      expect(trainingApiMocks.initTraining).toHaveBeenCalledWith({
        userId: 'frontend-training-user',
        characterId: null,
        trainingMode: 'guided',
        playerProfile: null,
      });
    });

    expect(await screen.findByText('Initial Briefing')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /Hold publication/ }));
    fireEvent.click(screen.getByRole('button', { name: '提交本轮训练' }));

    await waitFor(() => {
      expect(trainingApiMocks.submitTrainingRound).toHaveBeenCalledWith({
        sessionId: 'training-session-1',
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: 'scenario-1-opt-1',
      });
    });

    expect(await screen.findByText('Follow Up Interview')).toBeTruthy();
    expect(screen.getByText('confirmed timeline')).toBeTruthy();
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'in_progress',
    });
    expectTrainingInsightLinks(container, 'training-session-1');
  });

  it('restores a cached training session through the session summary endpoint on refresh', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-restore',
      trainingMode: 'adaptive',
      characterId: '12',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce({
      sessionId: 'training-session-restore',
      trainingMode: 'adaptive',
      status: 'in_progress',
      roundNo: 2,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-2', 2),
      progressAnchor: {
        roundNo: 2,
        totalRounds: 6,
        completedRounds: 2,
        remainingRounds: 4,
        progressPercent: 33.3,
        nextRoundNo: 3,
      },
      resumableScenario: createScenario('scenario-2', 'Restore Scenario'),
      scenarioCandidates: [],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: '2026-03-20T09:00:00Z',
      endTime: null,
    });

    const { container } = renderRouterApp(ROUTES.TRAINING);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
        'training-session-restore'
      );
    });

    expect(await screen.findByText('Restore Scenario')).toBeTruthy();
    expect(screen.getByText('training-session-restore')).toBeTruthy();
    expect(screen.getByText('33.3%')).toBeTruthy();
    expect(trainingApiMocks.initTraining).not.toHaveBeenCalled();
    expectTrainingInsightLinks(container, 'training-session-restore');
  });

  it('prefers the active in-memory session over a stale resume target during auto restore', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-stale',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce({
      sessionId: 'training-session-active',
      trainingMode: 'adaptive',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-active', 1),
      progressAnchor: {
        roundNo: 1,
        totalRounds: 6,
        completedRounds: 1,
        remainingRounds: 5,
        progressPercent: 16.67,
        nextRoundNo: 2,
      },
      resumableScenario: createScenario('scenario-active', 'Active Session Restore'),
      scenarioCandidates: [],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: '2026-03-20T09:15:00Z',
      endTime: null,
    });

    renderRouterApp(ROUTES.TRAINING, {
      activeSession: {
        sessionId: 'training-session-active',
        trainingMode: 'adaptive',
        characterId: '42',
        status: 'in_progress',
        roundNo: 1,
        totalRounds: 6,
        runtimeState: createRuntimeState('scenario-active', 1),
      },
    });

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
        'training-session-active'
      );
    });

    expect(await screen.findByText('Active Session Restore')).toBeTruthy();
    expect(screen.getByText('16.7%')).toBeTruthy();
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-active',
      trainingMode: 'adaptive',
      characterId: '42',
    });
  });

  it('clears the cached resume target when session summary recovery is terminally corrupted', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-broken',
      trainingMode: 'guided',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
        status: 409,
        message: 'training session recovery state corrupted',
      })
    );

    renderRouterApp(ROUTES.TRAINING);

    expect(
      await screen.findByText('训练会话恢复状态损坏，已清理本地恢复入口。')
    ).toBeTruthy();
    expect(readTrainingResumeTarget()).toBeNull();
    expect(screen.getByRole('button', { name: '启动训练' })).toBeTruthy();
  });
});
