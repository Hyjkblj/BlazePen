// @vitest-environment jsdom

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ROUTES } from '@/config/routes';
import {
  TrainingFlowProvider,
  useTrainingFlow,
  type ActiveTrainingSessionState,
} from '@/contexts';
import TrainingDiagnostics from '@/pages/TrainingDiagnostics';
import TrainingProgress from '@/pages/TrainingProgress';
import TrainingReport from '@/pages/TrainingReport';
import { ServiceError } from '@/services/serviceError';
import {
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';

const trainingApiMocks = vi.hoisted(() => ({
  getTrainingProgress: vi.fn(),
  getTrainingReport: vi.fn(),
  getTrainingDiagnostics: vi.fn(),
}));

vi.mock('@/services/trainingApi', () => trainingApiMocks);

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

function TrainingFlowStateProbe() {
  const { state } = useTrainingFlow();

  return (
    <output data-testid="training-active-session">
      {state.activeSession?.sessionId ?? 'none'}
    </output>
  );
}

const createRuntimeState = (sceneId: string, roundNo: number) => ({
  currentRoundNo: roundNo,
  currentSceneId: sceneId,
  kState: {
    K1: 0.45,
  },
  sState: {
    source_safety: 0.86,
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
    sourceSafety: 0.86,
  },
  playerProfile: null,
});

const renderInsightRoute = (
  initialEntry: string,
  { activeSession = null }: { activeSession?: ActiveTrainingSessionState | null } = {}
) =>
  render(
    <TrainingFlowProvider>
      <TrainingFlowSeed activeSession={activeSession}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <TrainingFlowStateProbe />
          <Routes>
            <Route path={ROUTES.TRAINING_PROGRESS} element={<TrainingProgress />} />
            <Route path={ROUTES.TRAINING_REPORT} element={<TrainingReport />} />
            <Route path={ROUTES.TRAINING_DIAGNOSTICS} element={<TrainingDiagnostics />} />
          </Routes>
        </MemoryRouter>
      </TrainingFlowSeed>
    </TrainingFlowProvider>
  );

describe('Training insight routes', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('loads training progress from the active in-memory session when no query sessionId is provided', async () => {
    trainingApiMocks.getTrainingProgress.mockResolvedValueOnce({
      sessionId: 'training-session-active',
      status: 'in_progress',
      roundNo: 2,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-active', 2),
    });

    renderInsightRoute(ROUTES.TRAINING_PROGRESS, {
      activeSession: {
        sessionId: 'training-session-active',
        trainingMode: 'guided',
        characterId: '42',
        status: 'in_progress',
        roundNo: 2,
        totalRounds: 6,
        runtimeState: createRuntimeState('scenario-active', 2),
      },
    });

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingProgress).toHaveBeenCalledWith(
        'training-session-active'
      );
    });

    expect(await screen.findByText('Training Progress')).toBeTruthy();
    expect(screen.getByText('33.3%')).toBeTruthy();
    expect(screen.getByText('scenario-active')).toBeTruthy();
  });

  it('prefers an explicit query sessionId over the active session on the report route', async () => {
    trainingApiMocks.getTrainingReport.mockResolvedValueOnce({
      sessionId: 'training-session-explicit',
      status: 'completed',
      rounds: 3,
      kStateFinal: {
        K1: 0.62,
      },
      sStateFinal: {
        source_safety: 0.9,
      },
      improvement: 0.31,
      playerProfile: null,
      runtimeState: createRuntimeState('scenario-explicit', 3),
      ending: null,
      summary: {
        weightedScoreInitial: 0.3,
        weightedScoreFinal: 0.71,
        weightedScoreDelta: 0.41,
        strongestImprovedSkillCode: 'K1',
        strongestImprovedSkillDelta: 0.31,
        weakestSkillCode: 'K2',
        weakestSkillScore: 0.22,
        dominantRiskFlag: 'source_exposure_risk',
        highRiskRoundCount: 1,
        highRiskRoundNos: [2],
        panicTriggerRoundCount: 0,
        sourceExposedRoundCount: 1,
        editorLockedRoundCount: 0,
        highRiskPathRoundCount: 0,
        branchTransitionCount: 1,
        branchTransitionRounds: [2],
        branchTransitions: [
          {
            sourceScenarioId: 'S1',
            targetScenarioId: 'S2',
            transitionType: 'branch',
            reason: 'source_warning',
            count: 1,
            roundNos: [2],
            triggeredFlags: ['source_warning'],
          },
        ],
        riskFlagCounts: [
          {
            code: 'source_exposure_risk',
            count: 1,
          },
        ],
        completedScenarioIds: ['S1', 'S2'],
        reviewSuggestions: ['优先补练来源保护'],
      },
      abilityRadar: [
        {
          code: 'K1',
          initial: 0.2,
          final: 0.6,
          delta: 0.4,
          weight: null,
          isLowestFinal: false,
          isHighestGain: true,
        },
      ],
      stateRadar: [],
      growthCurve: [
        {
          roundNo: 0,
          scenarioId: null,
          scenarioTitle: '初始状态',
          kState: {},
          sState: {},
          weightedKScore: 0.2,
          isHighRisk: false,
          riskFlags: [],
          primarySkillCode: null,
          timestamp: null,
        },
      ],
      history: [
        {
          roundNo: 1,
          scenarioId: 'S1',
          userInput: 'Protect the source',
          selectedOption: null,
          evaluation: null,
          kStateBefore: {},
          kStateAfter: {},
          sStateBefore: {},
          sStateAfter: {},
          timestamp: null,
          decisionContext: {
            mode: 'guided',
            selectionSource: 'manual',
            selectedScenarioId: 'S1',
            recommendedScenarioId: 'S2',
            candidatePool: [],
            selectedRecommendation: null,
            recommendedRecommendation: null,
            selectedBranchTransition: null,
            recommendedBranchTransition: null,
          },
          ktObservation: {
            scenarioId: 'S1',
            scenarioTitle: 'Initial Briefing',
            trainingMode: 'guided',
            roundNo: 1,
            primarySkillCode: 'K1',
            primaryRiskFlag: null,
            isHighRisk: false,
            targetSkills: [],
            weakSkillsBefore: [],
            riskFlags: [],
            focusTags: [],
            evidence: [],
            skillObservations: [],
            stateObservations: [],
            observationSummary: '',
          },
          runtimeState: null,
          consequenceEvents: [],
        },
      ],
    });

    renderInsightRoute(`${ROUTES.TRAINING_REPORT}?sessionId=training-session-explicit`, {
      activeSession: {
        sessionId: 'training-session-active',
        trainingMode: 'adaptive',
        characterId: '42',
        status: 'in_progress',
        roundNo: 2,
        totalRounds: 6,
        runtimeState: createRuntimeState('scenario-active', 2),
      },
    });

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingReport).toHaveBeenCalledWith(
        'training-session-explicit'
      );
    });

    expect(await screen.findByText('Training Report')).toBeTruthy();
    expect(screen.getByText('优先补练来源保护')).toBeTruthy();
    expect(screen.getByText('source_exposure_risk: 1')).toBeTruthy();
  });

  it('falls back to the persisted resume target for diagnostics after refresh', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-resume',
      trainingMode: 'guided',
      status: 'completed',
    });
    trainingApiMocks.getTrainingDiagnostics.mockResolvedValueOnce({
      sessionId: 'training-session-resume',
      status: 'completed',
      roundNo: 3,
      playerProfile: null,
      runtimeState: null,
      summary: {
        totalRecommendationLogs: 1,
        totalAuditEvents: 1,
        totalKtObservations: 1,
        highRiskRoundCount: 1,
        highRiskRoundNos: [2],
        recommendedVsSelectedMismatchCount: 0,
        recommendedVsSelectedMismatchRounds: [],
        riskFlagCounts: [
          {
            code: 'source_exposure_risk',
            count: 1,
          },
        ],
        primarySkillFocusCounts: [],
        topWeakSkills: [],
        selectionSourceCounts: [],
        eventTypeCounts: [],
        phaseTagCounts: [],
        phaseTransitionCount: 0,
        phaseTransitionRounds: [],
        panicTriggerRoundCount: 0,
        panicTriggerRounds: [],
        sourceExposedRoundCount: 0,
        sourceExposedRounds: [],
        editorLockedRoundCount: 0,
        editorLockedRounds: [],
        highRiskPathRoundCount: 0,
        highRiskPathRounds: [],
        branchTransitionCount: 0,
        branchTransitionRounds: [],
        branchTransitions: [],
        lastPrimarySkillCode: null,
        lastPrimaryRiskFlag: null,
        lastEventType: null,
        lastPhaseTags: [],
        lastBranchTransition: null,
      },
      recommendationLogs: [],
      auditEvents: [],
      ktObservations: [],
    });

    renderInsightRoute(ROUTES.TRAINING_DIAGNOSTICS);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingDiagnostics).toHaveBeenCalledWith(
        'training-session-resume'
      );
    });

    expect(await screen.findByText('Training Diagnostics')).toBeTruthy();
    expect(screen.getByText('source_exposure_risk: 1')).toBeTruthy();
  });

  it('shows an empty state when there is no readable session target', async () => {
    renderInsightRoute(ROUTES.TRAINING_DIAGNOSTICS);

    expect(await screen.findByText('暂无训练诊断')).toBeTruthy();
    expect(trainingApiMocks.getTrainingDiagnostics).not.toHaveBeenCalled();
  });

  it('surfaces structured diagnostics failures with a retry affordance', async () => {
    trainingApiMocks.getTrainingDiagnostics.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
        status: 409,
        message: 'training session recovery state corrupted',
      })
    );

    renderInsightRoute(`${ROUTES.TRAINING_DIAGNOSTICS}?sessionId=training-session-broken`);

    expect(await screen.findByText('训练会话恢复状态损坏，当前结果无法读取。')).toBeTruthy();
    expect(screen.getByRole('button', { name: '重新加载' })).toBeTruthy();
  });

  it('clears a broken cached diagnostics session and stays empty on the next refresh', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-broken',
      trainingMode: 'guided',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingDiagnostics.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SESSION_NOT_FOUND',
        status: 404,
        message: 'training session not found',
      })
    );

    const firstRender = renderInsightRoute(ROUTES.TRAINING_DIAGNOSTICS, {
      activeSession: {
        sessionId: 'training-session-broken',
        trainingMode: 'guided',
        characterId: '42',
        status: 'in_progress',
        roundNo: 1,
        totalRounds: 6,
        runtimeState: createRuntimeState('scenario-broken', 1),
      },
    });

    expect(await screen.findByText('训练会话不存在，请返回训练主页重新开始。')).toBeTruthy();
    expect(screen.getByTestId('training-active-session').textContent).toBe('none');
    expect(readTrainingResumeTarget()).toBeNull();
    expect(trainingApiMocks.getTrainingDiagnostics).toHaveBeenCalledTimes(1);

    firstRender.unmount();

    renderInsightRoute(ROUTES.TRAINING_DIAGNOSTICS);

    expect(await screen.findByText('暂无训练诊断')).toBeTruthy();
    expect(trainingApiMocks.getTrainingDiagnostics).toHaveBeenCalledTimes(1);
  });
});
