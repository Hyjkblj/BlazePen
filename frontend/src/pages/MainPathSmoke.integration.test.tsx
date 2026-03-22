// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { FeedbackProvider, GameFlowProvider, TrainingFlowProvider } from '@/contexts';
import { GAME_STORAGE_KEYS } from '@/storage/gameStorage';
import {
  getStoryEndingSummary,
  getStorySessionSnapshot,
  processGameInput,
} from '@/services/gameApi';
import Training from './Training';
import Game from './Game';

const gameApiMocks = vi.hoisted(() => ({
  initGame: vi.fn(),
  initializeStory: vi.fn(),
  getStorySessionSnapshot: vi.fn(),
  getStorySessionHistory: vi.fn(),
  getStoryEndingSummary: vi.fn(),
  processGameInput: vi.fn(),
  triggerEnding: vi.fn(),
}));

const trainingApiMocks = vi.hoisted(() => ({
  initTraining: vi.fn(),
  getTrainingSessionSummary: vi.fn(),
  submitTrainingRound: vi.fn(),
  getNextTrainingScenario: vi.fn(),
  getTrainingProgress: vi.fn(),
}));

vi.mock('@/services/gameApi', () => gameApiMocks);
vi.mock('@/services/trainingApi', () => trainingApiMocks);

vi.mock('@/hooks', async () => {
  const actual = await vi.importActual<typeof import('@/hooks')>('@/hooks');
  return {
    ...actual,
    useGameTts: vi.fn(),
  };
});

const seedStorySession = () => {
  sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-story');
  sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-1');
  sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, 'character-1');

  localStorage.setItem(
    'gameSave_thread-story',
    JSON.stringify({
      threadId: 'thread-story',
      characterId: 'character-1',
      messages: [{ role: 'assistant', content: 'The hallway goes silent.' }],
      snapshot: {
        currentDialogue: 'The hallway goes silent.',
        currentOptions: [{ id: 1, text: 'Investigate', type: 'action' }],
        currentScene: 'hallway',
        sceneImageUrl: '/scene.png',
        characterImageUrl: '/character.png',
        compositeImageUrl: null,
        shouldUseComposite: false,
        isGameFinished: false,
      },
      timestamp: 1,
    })
  );
};

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
  briefing: `${title} briefing`,
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

const renderStorySmokePage = () =>
  render(
    <FeedbackProvider>
      <GameFlowProvider>
        <Game />
      </GameFlowProvider>
    </FeedbackProvider>
  );

const renderTrainingSmokePage = () =>
  render(
    <MemoryRouter>
      <FeedbackProvider>
        <GameFlowProvider>
          <TrainingFlowProvider>
            <Training />
          </TrainingFlowProvider>
        </GameFlowProvider>
      </FeedbackProvider>
    </MemoryRouter>
  );

describe('main path smoke baseline', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.clearAllMocks();

    vi.mocked(getStoryEndingSummary).mockResolvedValue({
      threadId: 'thread-story',
      status: 'in_progress',
      roundNo: 1,
      hasEnding: false,
      ending: null,
      updatedAt: null,
      expiresAt: null,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('keeps the story turn submission happy path stable', async () => {
    seedStorySession();

    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce({
      threadId: 'thread-story',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'hallway',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'The hallway goes silent.',
      playerOptions: [{ id: 1, text: 'Investigate', type: 'action' }],
      isGameFinished: false,
      roundNo: 1,
      status: 'in_progress',
      updatedAt: '2026-03-22T10:00:00Z',
      expiresAt: '2026-03-22T10:30:00Z',
    });
    vi.mocked(processGameInput).mockResolvedValueOnce({
      threadId: 'thread-story',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'archive_room',
      sceneImageUrl: '/scene-next.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'A hidden drawer clicks open.',
      playerOptions: [{ id: 2, text: 'Open the drawer', type: 'action' }],
      isGameFinished: false,
    });

    renderStorySmokePage();

    fireEvent.click(await screen.findByRole('button', { name: 'Investigate' }));

    await waitFor(() => {
      expect(processGameInput).toHaveBeenCalledWith({
        threadId: 'thread-story',
        userInput: 'option:1',
        characterId: 'character-1',
      });
    });

    expect(await screen.findByText('A hidden drawer clicks open.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Open the drawer' })).toBeTruthy();
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

    renderTrainingSmokePage();

    expect(await screen.findByText('Training Frontend MVP')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '启动训练' }));

    expect(await screen.findByText('Initial Briefing')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /Hold publication/ }));
    fireEvent.click(screen.getByRole('button', { name: '提交本轮训练' }));

    expect(await screen.findByText('Follow Up Interview')).toBeTruthy();
    expect(screen.getByText('confirmed timeline')).toBeTruthy();
  });
});

