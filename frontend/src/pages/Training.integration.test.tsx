// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ROUTES,
} from '@/config/routes';
import {
  FeedbackProvider,
  TrainingFlowProvider,
  type ActiveTrainingSessionState,
} from '@/contexts';
import { ServiceError } from '@/services/serviceError';
import TrainingDiagnostics from '@/pages/TrainingDiagnostics';
import Training from '@/pages/Training';
import TrainingCinematicDemoPage from '@/pages/TrainingCinematicDemoPage';
import TrainingCompletion from '@/pages/TrainingCompletion';
import TrainingMainHomePage from '@/pages/TrainingMainHomePage';
import TrainingCodenameRevealPage from '@/pages/TrainingCodenameRevealPage';
import TrainingNewsroomIntroPage from '@/pages/TrainingNewsroomIntroPage';
import TrainingLandingPage from '@/pages/TrainingLandingPage';
import TrainingProgress from '@/pages/TrainingProgress';
import TrainingReport from '@/pages/TrainingReport';
import {
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';

const trainingApiMocks = vi.hoisted(() => ({
  initTraining: vi.fn(),
  bindTrainingSessionCharacter: vi.fn(),
  getTrainingSessionSummary: vi.fn(),
  submitTrainingRound: vi.fn(),
  getNextTrainingScenario: vi.fn(),
  createTrainingMediaTask: vi.fn(),
  getTrainingMediaTask: vi.fn(),
  getTrainingProgress: vi.fn(),
  getTrainingReport: vi.fn(),
  getTrainingDiagnostics: vi.fn(),
  buildTrainingSceneImageMediaTaskCreateParams: vi.fn((params: any) => ({
    sessionId: params.sessionId,
    roundNo: params.roundNo,
    taskType: 'image',
    idempotencyKey: `training-scene-image:${params.sessionId}:${params.scenario?.id}:attempt:${Math.max(
      0,
      Math.floor(params.attemptNo ?? 0)
    )}`,
    maxRetries: 1,
    payload: {},
  })),
}));

const trainingCharacterApiMocks = vi.hoisted(() => ({
  listTrainingIdentityPresets: vi.fn(),
  createTrainingCharacter: vi.fn(),
  createTrainingCharacterPreviewJob: vi.fn(),
  waitForTrainingCharacterPreviewJob: vi.fn(),
  getTrainingCharacterImages: vi.fn(),
  removeTrainingCharacterBackground: vi.fn(),
}));

vi.mock('@/services/trainingApi', () => trainingApiMocks);
vi.mock('@/services/trainingCharacterApi', () => trainingCharacterApiMocks);

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
    {
      id: `${id}-opt-2`,
      label: 'Clarify source chain',
      impactHint: 'Expand evidence scope',
    },
    {
      id: `${id}-opt-3`,
      label: 'Escalate to editor desk',
      impactHint: 'Reduce field risk first',
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

const renderRouterApp = (
  pathname: string,
  { activeSession = null }: { activeSession?: ActiveTrainingSessionState | null } = {}
) =>
  render(
    <FeedbackProvider>
      <TrainingFlowProvider initialActiveSession={activeSession}>
        <MemoryRouter initialEntries={[pathname]}>
          <Routes>
            <Route path={ROUTES.TRAINING} element={<Training />} />
            <Route path={ROUTES.TRAINING_COMPLETION} element={<TrainingCompletion />} />
            <Route path={ROUTES.TRAINING_MAINHOME} element={<TrainingMainHomePage />} />
            <Route path={ROUTES.TRAINING_LANDING} element={<TrainingLandingPage />} />
            <Route
              path={ROUTES.TRAINING_CODENAME_REVEAL}
              element={<TrainingCodenameRevealPage />}
            />
            <Route
              path={ROUTES.TRAINING_NEWSROOM_INTRO}
              element={<TrainingNewsroomIntroPage />}
            />
            <Route
              path={ROUTES.TRAINING_CINEMATIC_DEMO}
              element={<TrainingCinematicDemoPage />}
            />
            <Route path={ROUTES.TRAINING_PROGRESS} element={<TrainingProgress />} />
            <Route path={ROUTES.TRAINING_REPORT} element={<TrainingReport />} />
            <Route path={ROUTES.TRAINING_DIAGNOSTICS} element={<TrainingDiagnostics />} />
          </Routes>
        </MemoryRouter>
      </TrainingFlowProvider>
    </FeedbackProvider>
  );

const expectSceneImageByTitle = async (title: string) => {
  const sceneImage = await screen.findByRole('img', {
    name: new RegExp(title),
  });
  expect(sceneImage).toBeTruthy();
};

const clickLandingStartButton = async () => {
  const mainHomeStart = document.querySelector<HTMLButtonElement>('.training-mainhome__start');
  if (mainHomeStart) {
    fireEvent.click(mainHomeStart);
    await waitFor(() => {
      const identityInputs = document.querySelectorAll<HTMLInputElement>(
        '.training-landing__identity-group .ant-radio-input'
      );
      expect(identityInputs.length).toBeGreaterThan(0);
    });
  }

  const identityInputs = document.querySelectorAll<HTMLInputElement>(
    '.training-landing__identity-group .ant-radio-input'
  );
  fireEvent.click(identityInputs[0]);

  const generateButton = document.querySelector<HTMLButtonElement>(
    '.training-landing__preview-generate'
  );
  expect(generateButton).toBeTruthy();
  fireEvent.click(generateButton!);

  await waitFor(() => {
    const previewSlots = document.querySelectorAll<HTMLButtonElement>(
      '.training-landing__preview-slot:not(:disabled)'
    );
    expect(previewSlots.length).toBeGreaterThan(0);
  });

  const confirmButton = document.querySelector<HTMLButtonElement>('.training-landing__confirm');
  expect(confirmButton).toBeTruthy();
  fireEvent.click(confirmButton!);

  await waitFor(() => {
    const codenameReveal = document.querySelector<HTMLElement>('.training-codename-reveal');
    expect(codenameReveal).toBeTruthy();
  });
  const codenameReveal = document.querySelector<HTMLElement>('.training-codename-reveal');
  expect(codenameReveal).toBeTruthy();
  fireEvent.click(codenameReveal!);

  await waitFor(() => {
    const newsroomIntro = document.querySelector<HTMLElement>('.training-newsroom-intro');
    expect(newsroomIntro).toBeTruthy();
  });
  const newsroomIntro = document.querySelector<HTMLElement>('.training-newsroom-intro');
  expect(newsroomIntro).toBeTruthy();
  fireEvent.click(newsroomIntro!);

  await waitFor(() => {
    expect(screen.getByText('点击任意位置播放开场视频')).toBeTruthy();
  });
  fireEvent.click(newsroomIntro!);

  await waitFor(() => {
    const introVideo = document.querySelector<HTMLVideoElement>('.training-cinematic-video__video');
    expect(introVideo).toBeTruthy();
  });
  const introVideo = document.querySelector<HTMLVideoElement>('.training-cinematic-video__video');
  expect(introVideo).toBeTruthy();
  fireEvent.ended(introVideo!);
};

const submitFirstScenarioOption = async () => {
  const narration = document.querySelector<HTMLButtonElement>('.training-simplified__narration');
  if (narration) {
    fireEvent.click(narration);
  }

  await waitFor(
    () => {
      const optionButton = document.querySelector<HTMLButtonElement>(
        '.training-cinematic-choice-band__option'
      );
      expect(optionButton).toBeTruthy();
      fireEvent.click(optionButton!);
    },
    { timeout: 8000 }
  );
};

const expectTrainingEntryVisible = () => {
  const startEntry =
    document.querySelector<HTMLButtonElement>('.training-mainhome__start') ??
    document.querySelector<HTMLButtonElement>('.training-landing__start');
  const setupEntry = document.querySelector<HTMLButtonElement>('.training-landing__confirm');
  const restoreEntry = document.querySelector<HTMLButtonElement>('.training-landing__restore');
  const identityEntry = document.querySelector('.training-landing__identity-group');
  expect(Boolean(startEntry || setupEntry || restoreEntry || identityEntry)).toBe(true);
};

describe('Training route integration', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
    Object.values(trainingApiMocks).forEach((mockFn) => {
      mockFn.mockReset();
    });
    Object.values(trainingCharacterApiMocks).forEach((mockFn) => {
      mockFn.mockReset();
    });
    trainingCharacterApiMocks.listTrainingIdentityPresets.mockResolvedValue([
      {
        code: 'correspondent-female',
        title: 'War Correspondent',
        description: 'Integration preset',
        identity: 'field-reporter',
        defaultName: 'Frontline Reporter',
        defaultGender: 'female',
      },
    ]);
    trainingCharacterApiMocks.createTrainingCharacter.mockResolvedValue({
      characterId: '42',
      name: 'Frontline Reporter',
      imageUrl: null,
      imageUrls: [],
    });
    trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mockResolvedValue({
      jobId: 'preview-job-1',
      characterId: '42',
      idempotencyKey: 'preview-key-1',
      status: 'pending',
      imageUrls: [],
      errorMessage: null,
      createdAt: '2026-03-26T10:00:00',
      updatedAt: '2026-03-26T10:00:00',
    });
    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob.mockResolvedValue({
      jobId: 'preview-job-1',
      characterId: '42',
      idempotencyKey: 'preview-key-1',
      status: 'succeeded',
      imageUrls: ['/static/images/characters/training_integration_1.png'],
      errorMessage: null,
      createdAt: '2026-03-26T10:00:00',
      updatedAt: '2026-03-26T10:00:00',
    });
    trainingCharacterApiMocks.getTrainingCharacterImages.mockResolvedValue({
      images: ['/static/images/characters/training_integration_1.png'],
    });
    trainingCharacterApiMocks.removeTrainingCharacterBackground.mockResolvedValue({
      selected_image_url: '/static/images/characters/training_integration_1.png',
      transparent_url: '/static/images/characters/training_integration_1_transparent.png',
    });
    trainingApiMocks.bindTrainingSessionCharacter.mockImplementation(
      async (sessionId: string, characterId: number) => ({
        sessionId,
        characterId,
      })
    );
    trainingApiMocks.createTrainingMediaTask.mockImplementation(
      async ({ sessionId, roundNo }: { sessionId: string; roundNo?: number | null }) => ({
        taskId: `scene-task-${sessionId}-${roundNo ?? 0}`,
        sessionId,
        roundNo: roundNo ?? null,
        taskType: 'image',
        status: 'pending',
        result: null,
        error: null,
        createdAt: '2026-03-27T00:00:00Z',
        updatedAt: '2026-03-27T00:00:00Z',
        startedAt: null,
        finishedAt: null,
      })
    );
    trainingApiMocks.getTrainingMediaTask.mockResolvedValue({
      taskId: 'scene-task-default',
      sessionId: 'training-session-1',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      result: {
        preview_url: '/static/images/training/scene_default.png',
      },
      error: null,
      createdAt: '2026-03-27T00:00:00Z',
      updatedAt: '2026-03-27T00:00:01Z',
      startedAt: '2026-03-27T00:00:00Z',
      finishedAt: '2026-03-27T00:00:01Z',
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
      scenarioSequence: [],
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

    renderRouterApp(ROUTES.TRAINING_LANDING);

    await waitFor(() => {
      expectTrainingEntryVisible();
    });
    await clickLandingStartButton();

    await waitFor(() => {
      expect(trainingApiMocks.initTraining).toHaveBeenCalledWith(
        expect.objectContaining({
          userId: 'frontend-training-user',
          characterId: '42',
          trainingMode: 'guided',
          playerProfile: expect.objectContaining({
            age: null,
          }),
        })
      );
    });

    await expectSceneImageByTitle('Initial Briefing');

    await submitFirstScenarioOption();

    await waitFor(() => {
      expect(trainingApiMocks.submitTrainingRound).toHaveBeenCalledWith({
        sessionId: 'training-session-1',
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: 'scenario-1-opt-1',
      });
    });

    await expectSceneImageByTitle('Follow Up Interview');
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      status: 'in_progress',
    });
  });

  it('does not emit hook-order runtime errors when route redirect transitions into active training view', async () => {
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    try {
      renderRouterApp(ROUTES.TRAINING);
      await clickLandingStartButton();
      await expectSceneImageByTitle('Initial Briefing');

      const hookOrderErrors = consoleErrorSpy.mock.calls
        .map((call) => String(call[0] ?? ''))
        .filter(
          (message) =>
            message.includes('Rendered more hooks than during the previous render') ||
            message.includes('Rendered fewer hooks than expected')
        );
      expect(hookOrderErrors).toEqual([]);
    } finally {
      consoleErrorSpy.mockRestore();
    }
  });

  it('prefixes /static scene image urls with VITE_STATIC_ASSET_ORIGIN in training route', async () => {
    vi.stubEnv('VITE_STATIC_ASSET_ORIGIN', 'http://localhost:8010');
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-asset-origin',
      characterId: null,
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [{ id: 'scenario-1', title: 'Initial Briefing' }],
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValue(
      createSessionSummary('training-session-asset-origin', 'scenario-1', 'Initial Briefing')
    );
    trainingApiMocks.getTrainingMediaTask.mockResolvedValueOnce({
      taskId: 'scene-task-default',
      sessionId: 'training-session-asset-origin',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      result: {
        preview_url: '/static/images/training/scene_default.png',
      },
      error: null,
      createdAt: '2026-03-27T00:00:00Z',
      updatedAt: '2026-03-27T00:00:01Z',
      startedAt: '2026-03-27T00:00:00Z',
      finishedAt: '2026-03-27T00:00:01Z',
    });

    renderRouterApp(ROUTES.TRAINING);
    await waitFor(() => {
      expectTrainingEntryVisible();
    });
    await clickLandingStartButton();

    await waitFor(() => {
      const img = document.querySelector('img.training-simplified__scene-image');
      expect(img).toBeTruthy();
      expect(img?.getAttribute('src')).toBe('http://localhost:8010/static/images/training/scene_default.png');
    });
  });

  it('allows retrying scene image generation after create task failure on simplified page', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-retry-scene',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [],
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValue(
      createSessionSummary('training-session-retry-scene', 'scenario-1', 'Initial Briefing')
    );

    let createAttempts = 0;
    let allowCreateSuccess = false;
    trainingApiMocks.createTrainingMediaTask.mockImplementation(
      async ({ sessionId, roundNo }: { sessionId: string; roundNo?: number | null }) => {
        createAttempts += 1;
        if (!allowCreateSuccess) {
          throw new Error('scene image create failed');
        }
        return {
          taskId: `scene-task-${createAttempts}`,
          sessionId,
          roundNo: roundNo ?? null,
          taskType: 'image',
          status: 'pending',
          result: null,
          error: null,
          createdAt: '2026-03-27T00:00:00Z',
          updatedAt: '2026-03-27T00:00:00Z',
          startedAt: null,
          finishedAt: null,
        };
      }
    );
    trainingApiMocks.getTrainingMediaTask.mockImplementation(async (taskId: string) => ({
      taskId,
      sessionId: 'training-session-retry-scene',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      result: {
        preview_url: '/static/images/training/scene_retry.png',
      },
      error: null,
      createdAt: '2026-03-27T00:00:00Z',
      updatedAt: '2026-03-27T00:00:01Z',
      startedAt: '2026-03-27T00:00:00Z',
      finishedAt: '2026-03-27T00:00:01Z',
    }));

    renderRouterApp(ROUTES.TRAINING_LANDING);

    await waitFor(() => {
      expectTrainingEntryVisible();
    });
    await clickLandingStartButton();

    await waitFor(() => {
      expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalled();
    });

    const retryButton = await screen.findByRole('button', {
      name: /重新生成场景图/,
    });
    const attemptsBeforeRetry = createAttempts;
    allowCreateSuccess = true;
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(createAttempts).toBeGreaterThan(attemptsBeforeRetry);
    });
    await expectSceneImageByTitle('Initial Briefing');
  });

  it('allows retrying scene image generation after polling failure on simplified page', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-retry-poll',
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [],
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValue(
      createSessionSummary('training-session-retry-poll', 'scenario-1', 'Initial Briefing')
    );

    trainingApiMocks.createTrainingMediaTask.mockImplementation(
      async ({ sessionId, roundNo }: { sessionId: string; roundNo?: number | null }) => ({
        taskId: `scene-task-poll-${sessionId}-${roundNo ?? 0}`,
        sessionId,
        roundNo: roundNo ?? null,
        taskType: 'image',
        status: 'pending',
        result: null,
        error: null,
        createdAt: '2026-03-27T00:00:00Z',
        updatedAt: '2026-03-27T00:00:00Z',
        startedAt: null,
        finishedAt: null,
      })
    );

    let allowPollingSuccess = false;
    trainingApiMocks.getTrainingMediaTask.mockImplementation(async (taskId: string) => {
      if (!allowPollingSuccess) {
        return {
          taskId,
          sessionId: 'training-session-retry-poll',
          roundNo: 1,
          taskType: 'image',
          status: 'failed',
          result: null,
          error: { message: 'scene polling failed once' },
          createdAt: '2026-03-27T00:00:00Z',
          updatedAt: '2026-03-27T00:00:01Z',
          startedAt: '2026-03-27T00:00:00Z',
          finishedAt: '2026-03-27T00:00:01Z',
        };
      }
      return {
        taskId,
        sessionId: 'training-session-retry-poll',
        roundNo: 1,
        taskType: 'image',
        status: 'succeeded',
        result: {
          preview_url: '/static/images/training/scene_retry_poll.png',
        },
        error: null,
        createdAt: '2026-03-27T00:00:00Z',
        updatedAt: '2026-03-27T00:00:01Z',
        startedAt: '2026-03-27T00:00:00Z',
        finishedAt: '2026-03-27T00:00:01Z',
      };
    });

    renderRouterApp(ROUTES.TRAINING_LANDING);

    await waitFor(() => {
      expectTrainingEntryVisible();
    });
    await clickLandingStartButton();

    const retryButton = await screen.findByRole('button', {
      name: /重新生成场景图/,
    });
    allowPollingSuccess = true;
    fireEvent.click(retryButton);

    await expectSceneImageByTitle('Initial Briefing');
  });

  it('restores session summary when submit returns scenario mismatch', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-mismatch',
      characterId: null,
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [{ id: 'scenario-1', title: 'Initial Briefing' }],
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
    await expectSceneImageByTitle('Initial Briefing');

    await submitFirstScenarioOption();

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

    await expectSceneImageByTitle('Recovered Scenario');
    expect(
      screen.getByText(
        '\u63d0\u4ea4\u573a\u666f\u5df2\u53d8\u66f4\uff0c\u5df2\u6309\u670d\u52a1\u7aef\u6700\u65b0\u4f1a\u8bdd\u72b6\u6001\u6062\u590d\u3002'
      )
    ).toBeTruthy();
  });

  it('does not recreate scene image task when mismatch recovery keeps the same scenario', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-mismatch-same-scene',
      characterId: null,
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [{ id: 'scenario-1', title: 'Initial Briefing' }],
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
        createSessionSummary('training-session-mismatch-same-scene', 'scenario-1', 'Initial Briefing')
      )
      .mockResolvedValueOnce(
        createSessionSummary('training-session-mismatch-same-scene', 'scenario-1', 'Initial Briefing')
      )
      .mockResolvedValueOnce(
        createSessionSummary('training-session-mismatch-same-scene', 'scenario-1', 'Initial Briefing')
      )
      .mockResolvedValueOnce(
        createSessionSummary('training-session-mismatch-same-scene', 'scenario-1', 'Initial Briefing')
      );

    renderRouterApp(ROUTES.TRAINING);

    await clickLandingStartButton();
    await expectSceneImageByTitle('Initial Briefing');

    await waitFor(() => {
      expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalled();
    });
    const createTaskCallsBeforeRecovery = trainingApiMocks.createTrainingMediaTask.mock.calls.length;
    expect(createTaskCallsBeforeRecovery).toBeGreaterThan(0);

    await submitFirstScenarioOption();

    await waitFor(() => {
      expect(trainingApiMocks.submitTrainingRound).toHaveBeenCalledWith({
        sessionId: 'training-session-mismatch-same-scene',
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: 'scenario-1-opt-1',
      });
    });
    await waitFor(() => {
      expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
        'training-session-mismatch-same-scene'
      );
    });

    await expectSceneImageByTitle('Initial Briefing');
    const createTaskCallsAfterRecovery = trainingApiMocks.createTrainingMediaTask.mock.calls.length;
    expect(createTaskCallsAfterRecovery).toBeLessThanOrEqual(createTaskCallsBeforeRecovery + 1);
  });

  it('retries with a new attempt when scene image create returns conflict with mismatched scope', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-conflict-mismatch',
      characterId: null,
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [{ id: 'scenario-1', title: 'Initial Briefing' }],
    });
    trainingApiMocks.getTrainingSessionSummary.mockResolvedValue(
      createSessionSummary('training-session-conflict-mismatch', 'scenario-1', 'Initial Briefing')
    );

    let createCalls = 0;
    trainingApiMocks.createTrainingMediaTask.mockImplementation(async () => {
      createCalls += 1;
      if (createCalls === 1) {
        throw new ServiceError({
          code: 'TRAINING_MEDIA_TASK_CONFLICT',
          status: 409,
          message: 'idempotency conflict',
          details: {
            task_id: 'existing-task-1',
            idempotency_key: 'training-scene-image:other-session:scenario-1:attempt:0',
            session_id: 'other-session',
            existing_scope: { round_no: 99 },
          },
        });
      }
      return {
        taskId: 'scene-task-conflict-retry',
        sessionId: 'training-session-conflict-mismatch',
        roundNo: 1,
        taskType: 'image',
        status: 'pending',
        result: null,
        error: null,
        createdAt: '2026-03-27T00:00:00Z',
        updatedAt: '2026-03-27T00:00:00Z',
        startedAt: null,
        finishedAt: null,
      };
    });
    trainingApiMocks.getTrainingMediaTask.mockResolvedValueOnce({
      taskId: 'scene-task-conflict-retry',
      sessionId: 'training-session-conflict-mismatch',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      result: {
        preview_url: '/static/images/training/scene_conflict_retry.png',
      },
      error: null,
      createdAt: '2026-03-27T00:00:00Z',
      updatedAt: '2026-03-27T00:00:01Z',
      startedAt: '2026-03-27T00:00:00Z',
      finishedAt: '2026-03-27T00:00:01Z',
    });

    renderRouterApp(ROUTES.TRAINING);
    await clickLandingStartButton();

    await waitFor(() => {
      expect(trainingApiMocks.createTrainingMediaTask).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(trainingApiMocks.createTrainingMediaTask.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    await expectSceneImageByTitle('Initial Briefing');
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
    await waitFor(() => {
      expectTrainingEntryVisible();
    });
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

    const restoreButton = await waitFor(() => {
      const button = document.querySelector<HTMLButtonElement>('.training-landing__restore');
      expect(button).toBeTruthy();
      return button!;
    });
    fireEvent.click(restoreButton!);

    await waitFor(() => {
      expect(trainingApiMocks.getTrainingSessionSummary).toHaveBeenCalledWith(
        'training-session-restore'
      );
    });
    await expectSceneImageByTitle('Restore Scenario');
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

    await expectSceneImageByTitle('Active Session Restore');
    expect(readTrainingResumeTarget()).toMatchObject({
      sessionId: 'training-session-active',
      trainingMode: 'adaptive',
      characterId: '58',
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
    await expectSceneImageByTitle('Explicit Route Restore');
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
    await waitFor(() => {
      expectTrainingEntryVisible();
    });
  });
});
