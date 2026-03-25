// @vitest-environment jsdom

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ROUTES,
} from '@/config/routes';
import {
  FeedbackProvider,
  TrainingFlowProvider,
  useTrainingFlow,
  type ActiveTrainingSessionState,
} from '@/contexts';
import { ServiceError } from '@/services/serviceError';
import TrainingDiagnostics from '@/pages/TrainingDiagnostics';
import Training from '@/pages/Training';
import TrainingMainHomePage from '@/pages/TrainingMainHomePage';
import TrainingLandingPage from '@/pages/TrainingLandingPage';
import TrainingProgress from '@/pages/TrainingProgress';
import TrainingReport from '@/pages/TrainingReport';
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
  getTrainingReport: vi.fn(),
  getTrainingDiagnostics: vi.fn(),
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

const createSessionSummary = (
  sessionId: string,
  sceneId: string,
  sceneTitle: string
) => ({
  sessionId,
  characterId: '42',
  trainingMode: 'guided' as const,
  status: 'in_progress',
  roundNo: 0,
  totalRounds: 6,
  runtimeState: createRuntimeState(sceneId, 0),
  progressAnchor: {
    roundNo: 0,
    totalRounds: 6,
    completedRounds: 0,
    remainingRounds: 6,
    progressPercent: 0,
    nextRoundNo: 1,
  },
  resumableScenario: createScenario(sceneId, sceneTitle),
  scenarioCandidates: [],
  canResume: true,
  isCompleted: false,
  createdAt: null,
  updatedAt: null,
  endTime: null,
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
              <Route path={ROUTES.TRAINING_MAINHOME} element={<TrainingMainHomePage />} />
              <Route path={ROUTES.TRAINING_LANDING} element={<TrainingLandingPage />} />
              <Route path={ROUTES.TRAINING_PROGRESS} element={<TrainingProgress />} />
              <Route path={ROUTES.TRAINING_REPORT} element={<TrainingReport />} />
              <Route path={ROUTES.TRAINING_DIAGNOSTICS} element={<TrainingDiagnostics />} />
            </Routes>
          </MemoryRouter>
        </TrainingFlowSeed>
      </TrainingFlowProvider>
    </FeedbackProvider>
  );

const expectTrainingInsightLinks = () => {
  const subnavButtons = document.querySelectorAll('.training-shell__subnav .training-shell__subnav-link');
  expect(subnavButtons.length).toBe(3);
};

const clickLandingStartButton = async () => {
  const mainHomeStart = document.querySelector<HTMLButtonElement>('.training-mainhome__start');
  if (mainHomeStart) {
    fireEvent.click(mainHomeStart);
    await waitFor(() => {
      const hasLandingStart = Boolean(document.querySelector('.training-landing__start'));
      const identityInputs = document.querySelectorAll<HTMLInputElement>(
        '.training-landing__identity-group .ant-radio-input'
      );
      expect(hasLandingStart || identityInputs.length > 0).toBe(true);
    });
  }

  const landingStart = document.querySelector<HTMLButtonElement>('.training-landing__start');
  if (landingStart) {
    fireEvent.click(landingStart);
  }

  await waitFor(() => {
    const identityInputs = document.querySelectorAll<HTMLInputElement>(
      '.training-landing__identity-group .ant-radio-input'
    );
    expect(identityInputs.length).toBeGreaterThan(0);
  });
  const identityInputs = document.querySelectorAll<HTMLInputElement>(
    '.training-landing__identity-group .ant-radio-input'
  );
  fireEvent.click(identityInputs[0]);
  const imageCards = document.querySelectorAll<HTMLButtonElement>('.training-landing__image-card');
  expect(imageCards.length).toBeGreaterThan(0);
  fireEvent.click(imageCards[0]);
  const confirmButton = document.querySelector<HTMLButtonElement>('.training-landing__confirm');
  expect(confirmButton).toBeTruthy();
  fireEvent.click(confirmButton!);
};

const submitFirstScenarioOption = () => {
  const optionInputs = document.querySelectorAll<HTMLInputElement>(
    '.training-shell__option-list .ant-radio-input'
  );
  expect(optionInputs.length).toBeGreaterThan(0);
  fireEvent.click(optionInputs[0]);

  const submitButton = document.querySelector<HTMLButtonElement>(
    '.training-shell__panel--primary .training-shell__primary-button'
  );
  expect(submitButton).toBeTruthy();
  fireEvent.click(submitButton!);
};

const expectTrainingEntryVisible = () => {
  const startEntry =
    document.querySelector<HTMLButtonElement>('.training-mainhome__start') ??
    document.querySelector<HTMLButtonElement>('.training-landing__start');
  const setupEntry = document.querySelector<HTMLButtonElement>('.training-landing__confirm');
  expect(Boolean(startEntry || setupEntry)).toBe(true);
};

describe('Training route integration', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
    Object.values(trainingApiMocks).forEach((mockFn) => {
      mockFn.mockReset();
    });
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
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValue(
      createSessionSummary('training-session-1', 'scenario-1', 'Initial Briefing')
    );
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

    renderRouterApp(ROUTES.TRAINING);

    await waitFor(() => {
      expect(document.querySelector('.training-mainhome__start')).toBeTruthy();
    });
    await clickLandingStartButton();

    await waitFor(() => {
      expect(trainingApiMocks.initTraining).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 'frontend-training-user',
          characterId: null,
          trainingMode: 'guided',
          playerProfile: expect.objectContaining({
            age: null,
          }),
        })
      );
    });

    expect(await screen.findByText('Initial Briefing')).toBeTruthy();

    submitFirstScenarioOption();

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
    expectTrainingInsightLinks();
  });

  it('restores session summary when submit returns scenario mismatch', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-mismatch',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
    });
    trainingApiMocks.submitTrainingRound.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_SCENARIO_MISMATCH',
        status: 409,
        message: 'scenario mismatch',
      })
    );
    trainingApiMocks.getTrainingSessionSummary
      .mockResolvedValueOnce(
        createSessionSummary('training-session-mismatch', 'scenario-1', 'Initial Briefing')
      )
      .mockResolvedValueOnce({
        sessionId: 'training-session-mismatch',
        characterId: '12',
        trainingMode: 'guided',
        status: 'in_progress',
        roundNo: 1,
        totalRounds: 6,
        runtimeState: createRuntimeState('scenario-2', 1),
        progressAnchor: {
          roundNo: 1,
          totalRounds: 6,
          completedRounds: 1,
          remainingRounds: 5,
          progressPercent: 16.67,
          nextRoundNo: 2,
        },
        resumableScenario: createScenario('scenario-2', 'Recovered Scenario', 'Delay publication'),
        scenarioCandidates: [],
        canResume: true,
        isCompleted: false,
        createdAt: null,
        updatedAt: '2026-03-23T12:00:00Z',
        endTime: null,
      });

    renderRouterApp(ROUTES.TRAINING);

    await clickLandingStartButton();
    expect(await screen.findByText('Initial Briefing')).toBeTruthy();

    submitFirstScenarioOption();

    await waitFor(() => {
      expect(trainingApiMocks.submitTrainingRound).toHaveBeenCalledWith({
        sessionId: 'training-session-mismatch',
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: 'scenario-1-opt-1',
      });
    });
    await waitFor(() => {
      expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
        'training-session-mismatch'
      );
    });

    expect(await screen.findByText('Recovered Scenario')).toBeTruthy();
    expect(
      screen.getByText(
        '\u63d0\u4ea4\u573a\u666f\u5df2\u53d8\u66f4\uff0c\u5df2\u6309\u670d\u52a1\u7aef\u6700\u65b0\u4f1a\u8bdd\u72b6\u6001\u6062\u590d\u3002'
      )
    ).toBeTruthy();
    expectTrainingInsightLinks();
  });

  it('does not auto-restore from cached resume target without explicit or active session', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-restore',
      trainingMode: 'adaptive',
      characterId: '12',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce({
      sessionId: 'training-session-restore',
      characterId: '12',
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

    renderRouterApp(ROUTES.TRAINING);

    expect(trainingApiMocks.getTrainingSessionSummary).not.toHaveBeenCalled();
    expect(screen.queryByText('Restore Scenario')).toBeNull();
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-restore',
      trainingMode: 'adaptive',
      characterId: '12',
    });
    expect(trainingApiMocks.initTraining).not.toHaveBeenCalled();
    expectTrainingEntryVisible();
  });

  it('allows manual restore from landing when cached resume target exists', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-restore',
      trainingMode: 'adaptive',
      characterId: '12',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValue(
      createSessionSummary('training-session-restore', 'scenario-2', 'Restore Scenario')
    );

    renderRouterApp(ROUTES.TRAINING);

    expect(trainingApiMocks.getTrainingSessionSummary).not.toHaveBeenCalled();

    const restoreButton = document.querySelector<HTMLButtonElement>('.training-landing__restore');
    expect(restoreButton).toBeTruthy();
    fireEvent.click(restoreButton!);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
        'training-session-restore'
      );
    });
    expect(await screen.findByText('Restore Scenario')).toBeTruthy();
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
      characterId: '58',
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
    trainingApiMocks.getTrainingProgress.mockResolvedValueOnce({
      sessionId: 'training-session-active',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-active', 1),
      decisionContext: null,
      consequenceEvents: [],
    });
    trainingApiMocks.getTrainingReport.mockResolvedValueOnce({
      sessionId: 'training-session-active',
      status: 'in_progress',
      rounds: 1,
      kStateFinal: {
        K1: 0.45,
      },
      sStateFinal: {
        source_safety: 0.88,
      },
      improvement: 0.05,
      playerProfile: null,
      runtimeState: createRuntimeState('scenario-active', 1),
      ending: null,
      summary: null,
      abilityRadar: [],
      stateRadar: [],
      growthCurve: [],
      history: [],
    });
    trainingApiMocks.getTrainingDiagnostics.mockResolvedValueOnce({
      sessionId: 'training-session-active',
      status: 'in_progress',
      roundNo: 1,
      playerProfile: null,
      runtimeState: createRuntimeState('scenario-active', 1),
      summary: null,
      recommendationLogs: [],
      auditEvents: [],
      ktObservations: [],
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

    expect(await screen.findByText('training-session-active')).toBeTruthy();
    expect(screen.getByText('16.7%')).toBeTruthy();
    expectTrainingInsightLinks();
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-active',
      trainingMode: 'adaptive',
      characterId: '58',
    });

    const trainingSubnavLinks = document.querySelectorAll<HTMLButtonElement>(
      '.training-shell__subnav .training-shell__subnav-link'
    );
    expect(trainingSubnavLinks.length).toBe(3);
    fireEvent.click(trainingSubnavLinks[0]);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingProgress).toHaveBeenCalledWith(
        'training-session-active'
      );
    });

    const reportLink = document.querySelector<HTMLAnchorElement>(
      '.training-insight-shell__nav-link[href*=\"/training/report\"]'
    );
    expect(reportLink).toBeTruthy();
    fireEvent.click(reportLink!);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingReport).toHaveBeenCalledWith(
        'training-session-active'
      );
    });

    const diagnosticsLink = document.querySelector<HTMLAnchorElement>(
      '.training-insight-shell__nav-link[href*=\"/training/diagnostics\"]'
    );
    expect(diagnosticsLink).toBeTruthy();
    fireEvent.click(diagnosticsLink!);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingDiagnostics).toHaveBeenCalledWith(
        'training-session-active'
      );
    });
  });

  it('prefers explicit query sessionId over active and cached sessions on training route', async () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-stale',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValueOnce({
      sessionId: 'training-session-explicit',
      characterId: '58',
      trainingMode: 'adaptive',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-explicit', 1),
      progressAnchor: {
        roundNo: 1,
        totalRounds: 6,
        completedRounds: 1,
        remainingRounds: 5,
        progressPercent: 16.67,
        nextRoundNo: 2,
      },
      resumableScenario: createScenario('scenario-explicit', 'Explicit Route Restore'),
      scenarioCandidates: [],
      canResume: true,
      isCompleted: false,
      createdAt: null,
      updatedAt: '2026-03-20T10:15:00Z',
      endTime: null,
    });

    renderRouterApp(`${ROUTES.TRAINING}?sessionId=training-session-explicit`, {
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
        'training-session-explicit'
      );
    });
    expect(trainingApiMocks.getTrainingSessionSummary).not.toHaveBeenCalledWith(
      'training-session-active'
    );
    expect(await screen.findByText('Explicit Route Restore')).toBeTruthy();
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-explicit',
      trainingMode: 'adaptive',
      characterId: '58',
    });
  });

  it('keeps cached resume target untouched until a restore path is explicitly triggered', async () => {
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

    expect(trainingApiMocks.getTrainingSessionSummary).not.toHaveBeenCalled();
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-broken',
      trainingMode: 'guided',
      status: 'in_progress',
    });
    expectTrainingEntryVisible();
  });
});

