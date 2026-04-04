// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
    <TrainingFlowProvider initialActiveSession={activeSession}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <TrainingFlowStateProbe />
        <Routes>
          <Route path={ROUTES.TRAINING_PROGRESS} element={<TrainingProgress />} />
          <Route path={ROUTES.TRAINING_REPORT} element={<TrainingReport />} />
          <Route path={ROUTES.TRAINING_DIAGNOSTICS} element={<TrainingDiagnostics />} />
        </Routes>
      </MemoryRouter>
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
      decisionContext: {
        mode: 'guided',
        selectionSource: 'candidate_pool',
        selectedScenarioId: 'scenario-active',
        recommendedScenarioId: 'scenario-recommended',
        candidatePool: [],
        selectedRecommendation: null,
        recommendedRecommendation: null,
        selectedBranchTransition: {
          sourceScenarioId: 'scenario-previous',
          targetScenarioId: 'scenario-active',
          transitionType: 'branch',
          reason: 'source_warning',
          triggeredFlags: ['source_warning'],
          matchedRule: {},
        },
        recommendedBranchTransition: null,
      },
      consequenceEvents: [
        {
          eventType: 'source_warning',
          label: 'Source Warning',
          summary: 'Need verification before publish.',
          severity: 'high',
          roundNo: 2,
          relatedFlag: null,
          stateBar: null,
          payload: {},
        },
      ],
      ending: null,
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

    expect(
      await screen.findByRole('heading', { level: 1, name: '学习进度' })
    ).toBeTruthy();
    expect(screen.getByText('33.3%')).toBeTruthy();
    expect(screen.getAllByText('scenario-active').length).toBeGreaterThan(0);
    expect(screen.getByText('candidate_pool')).toBeTruthy();
    expect(screen.getByText(/Source Warning/)).toBeTruthy();
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

    expect(
      await screen.findByRole('heading', { level: 1, name: '学习总结' })
    ).toBeTruthy();
    expect(screen.getByText('优先补练来源保护')).toBeTruthy();
    expect(screen.getByText('source_exposure_risk: 1')).toBeTruthy();
  });

  it('shows an in-progress notice when the report session is not completed', async () => {
    trainingApiMocks.getTrainingReport.mockResolvedValueOnce({
      sessionId: 'training-session-in-progress',
      status: 'in_progress',
      rounds: 2,
      kStateFinal: {
        K1: 0.56,
      },
      sStateFinal: {
        source_safety: 0.89,
      },
      improvement: 0.22,
      playerProfile: null,
      runtimeState: createRuntimeState('scenario-active', 2),
      ending: null,
      summary: null,
      abilityRadar: [],
      stateRadar: [],
      growthCurve: [],
      history: [],
    });

    renderInsightRoute(`${ROUTES.TRAINING_REPORT}?sessionId=training-session-in-progress`);

    expect(
      await screen.findByRole('heading', { level: 1, name: '学习总结' })
    ).toBeTruthy();
    expect(await screen.findByText('学习总结还在更新')).toBeTruthy();
    expect(
      screen.getByText(
        '当前学习会话状态为',
        {
          exact: false,
        }
      )
    ).toBeTruthy();
  });

  it('treats dirty query sessionId as absent and keeps insight navigation canonical', async () => {
    trainingApiMocks.getTrainingReport.mockResolvedValueOnce({
      sessionId: 'training-session-active',
      status: 'completed',
      rounds: 2,
      kStateFinal: {
        K1: 0.6,
      },
      sStateFinal: {
        source_safety: 0.9,
      },
      improvement: 0.2,
      playerProfile: null,
      runtimeState: createRuntimeState('scenario-active', 2),
      ending: null,
      summary: null,
      abilityRadar: [],
      stateRadar: [],
      growthCurve: [],
      history: [],
    });

    renderInsightRoute(`${ROUTES.TRAINING_REPORT}?sessionId=%20UNDEFINED%20`, {
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
        'training-session-active'
      );
    });

    expect(
      await screen.findByRole('heading', { level: 1, name: '学习总结' })
    ).toBeTruthy();
    expect(screen.getByText('小结字段暂未齐')).toBeTruthy();
    expect(screen.getByRole('link', { name: '学习进度' }).getAttribute('href')).toBe(
      ROUTES.TRAINING_PROGRESS
    );
    expect(screen.getByRole('link', { name: '学习总结' }).getAttribute('href')).toBe(
      ROUTES.TRAINING_REPORT
    );
    expect(screen.getByRole('link', { name: '学情诊断' }).getAttribute('href')).toBe(
      ROUTES.TRAINING_DIAGNOSTICS
    );
  });

  it('keeps the last successful report visible when reloading the same session times out', async () => {
    trainingApiMocks.getTrainingReport
      .mockResolvedValueOnce({
        sessionId: 'training-session-report',
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
          branchTransitions: [],
          riskFlagCounts: [],
          completedScenarioIds: ['S1', 'S2'],
          reviewSuggestions: ['优先补练来源保护'],
        },
        abilityRadar: [],
        stateRadar: [],
        growthCurve: [],
        history: [],
      })
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          status: 504,
          message: 'training report timed out',
        })
      );

    renderInsightRoute(`${ROUTES.TRAINING_REPORT}?sessionId=training-session-report`);

    expect(
      await screen.findByRole('heading', { level: 1, name: '学习总结' })
    ).toBeTruthy();
    expect(screen.getByText('优先补练来源保护')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '刷新读取' }));

    expect(await screen.findByText('训练结果读取超时，请重试。')).toBeTruthy();
    expect(
      screen.getByText('当前显示的是最近一次成功读取的训练结果。可以稍后重新加载以获取最新状态。')
    ).toBeTruthy();
    expect(screen.getByText('优先补练来源保护')).toBeTruthy();
    expect(trainingApiMocks.getTrainingReport).toHaveBeenCalledTimes(2);
  });

  it('does not read diagnostics from persisted resumeTarget without explicit or active session', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-resume',
      trainingMode: 'guided',
      status: 'completed',
    });

    renderInsightRoute(ROUTES.TRAINING_DIAGNOSTICS);

    expect(await screen.findByText('暂时看不到学情诊断')).toBeTruthy();
    expect(trainingApiMocks.getTrainingDiagnostics).not.toHaveBeenCalled();
  });

  it('shows an empty state when there is no readable session target', async () => {
    renderInsightRoute(ROUTES.TRAINING_DIAGNOSTICS);

    expect(await screen.findByText('暂时看不到学情诊断')).toBeTruthy();
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

    expect(await screen.findByText('暂时看不到学情诊断')).toBeTruthy();
    expect(trainingApiMocks.getTrainingDiagnostics).toHaveBeenCalledTimes(1);
  });
});
