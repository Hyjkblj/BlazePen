// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { FeedbackProvider, TrainingFlowProvider } from '@/contexts';
import Training from './Training';
import TrainingCinematicDemoPage from './TrainingCinematicDemoPage';
import TrainingCodenameRevealPage from './TrainingCodenameRevealPage';
import TrainingNewsroomIntroPage from './TrainingNewsroomIntroPage';
import TrainingMainHomePage from './TrainingMainHomePage';
import TrainingLandingPage from './TrainingLandingPage';

const trainingApiMocks = vi.hoisted(() => ({
  initTraining: vi.fn(),
  bindTrainingSessionCharacter: vi.fn(),
  getTrainingSessionSummary: vi.fn(),
  submitTrainingRound: vi.fn(),
  getNextTrainingScenario: vi.fn(),
  createTrainingMediaTask: vi.fn(),
  getTrainingMediaTask: vi.fn(),
  getTrainingProgress: vi.fn(),
  buildTrainingSceneImageMediaTaskCreateParams: vi.fn((params: any) => ({
    sessionId: params.sessionId,
    roundNo: params.roundNo,
    taskType: 'image',
    idempotencyKey: `training-scene-image:${params.sessionId}:${params.scenario?.id}:attempt:0`,
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

const renderTrainingSmokePage = () =>
  render(
    <MemoryRouter initialEntries={[ROUTES.TRAINING]}>
      <FeedbackProvider>
        <TrainingFlowProvider>
          <Routes>
            <Route path={ROUTES.TRAINING} element={<Training />} />
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
          </Routes>
        </TrainingFlowProvider>
      </FeedbackProvider>
    </MemoryRouter>
  );

describe('training main path smoke baseline', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.clearAllMocks();
    trainingCharacterApiMocks.listTrainingIdentityPresets.mockResolvedValue([
      {
        code: 'correspondent-female',
        title: '战地记者（女）',
        description: 'Smoke preset',
        identity: '战地记者',
        defaultName: '前线女记者',
        defaultGender: 'female',
      },
    ]);
    trainingCharacterApiMocks.createTrainingCharacter.mockResolvedValue({
      characterId: '42',
      name: '前线女记者',
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
      imageUrls: ['/static/images/characters/training_smoke_1.png'],
      errorMessage: null,
      createdAt: '2026-03-26T10:00:00',
      updatedAt: '2026-03-26T10:00:00',
    });
    trainingCharacterApiMocks.getTrainingCharacterImages.mockResolvedValue({
      images: ['/static/images/characters/training_smoke_1.png'],
    });
    trainingCharacterApiMocks.removeTrainingCharacterBackground.mockResolvedValue({
      selected_image_url: '/static/images/characters/training_smoke_1.png',
      transparent_url: '/static/images/characters/training_smoke_1_transparent.png',
    });
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

  it('keeps the training initialization and submit happy path stable', async () => {
    trainingApiMocks.initTraining.mockResolvedValueOnce({
      sessionId: 'training-session-1',
      characterId: null,
      trainingMode: 'guided',
      status: 'initialized',
      roundNo: 0,
      runtimeState: createRuntimeState('scenario-1', 0),
      nextScenario: createScenario('scenario-1', 'Initial Briefing'),
      scenarioCandidates: [],
      scenarioSequence: [{ id: 'scenario-1', title: 'Initial Briefing' }],
    });
    trainingApiMocks.bindTrainingSessionCharacter.mockResolvedValue({
      sessionId: 'training-session-1',
      characterId: 42,
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
      consequenceEvents: [],
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

    renderTrainingSmokePage();

    await waitFor(() => {
      expect(document.querySelector('.training-mainhome__start')).toBeTruthy();
    });

    const mainHomeStart = document.querySelector<HTMLButtonElement>('.training-mainhome__start');
    if (mainHomeStart) {
      fireEvent.click(mainHomeStart);
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

    const initialSceneImage = await screen.findByRole('img', {
      name: /Initial Briefing/,
    });
    expect(initialSceneImage).toBeTruthy();

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

    await waitFor(() => {
      expect(trainingApiMocks.submitTrainingRound).toHaveBeenCalledWith({
        sessionId: 'training-session-1',
        scenarioId: 'scenario-1',
        userInput: 'Hold publication',
        selectedOption: 'scenario-1-opt-1',
      });
    });

    const followUpSceneImage = await screen.findByRole('img', {
      name: /Follow Up Interview/,
    });
    expect(followUpSceneImage).toBeTruthy();
  });
});

