// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { FeedbackProvider, TrainingFlowProvider } from '@/contexts';
import Training from './Training';
import TrainingMainHomePage from './TrainingMainHomePage';
import TrainingLandingPage from './TrainingLandingPage';

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
  });

  afterEach(() => {
    cleanup();
  });

  it('keeps the training initialization and submit happy path stable', async () => {
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
      const hasLandingStart = Boolean(document.querySelector('.training-landing__start'));
      const identityInputs = document.querySelectorAll<HTMLInputElement>(
        '.training-landing__identity-group .ant-radio-input'
      );
      expect(hasLandingStart || identityInputs.length > 0).toBe(true);
    });
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

    expect(await screen.findByText('Initial Briefing')).toBeTruthy();

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
  });
});

