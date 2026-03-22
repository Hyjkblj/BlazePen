// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { FeedbackProvider, TrainingFlowProvider } from '@/contexts';
import Training from './Training';

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

const renderTrainingSmokePage = () =>
  render(
    <MemoryRouter initialEntries={[ROUTES.TRAINING]}>
      <FeedbackProvider>
        <TrainingFlowProvider>
          <Routes>
            <Route path={ROUTES.TRAINING} element={<Training />} />
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

    const { container } = renderTrainingSmokePage();

    expect(await screen.findByText('Training Frontend MVP')).toBeTruthy();

    const startButton = container.querySelector(
      '.training-shell__panel--primary .training-shell__primary-button'
    );
    expect(startButton).toBeTruthy();
    fireEvent.click(startButton!);

    expect(await screen.findByText('Initial Briefing')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /Hold publication/ }));

    const submitButton = container.querySelector(
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
