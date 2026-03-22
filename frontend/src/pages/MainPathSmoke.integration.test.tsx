// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import { GAME_STORAGE_KEYS } from '@/storage/gameStorage';
import {
  getStoryEndingSummary,
  getStorySessionSnapshot,
  processGameInput,
} from '@/services/gameApi';
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

vi.mock('@/services/gameApi', () => gameApiMocks);

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

const renderStorySmokePage = () =>
  render(
    <FeedbackProvider>
      <GameFlowProvider>
        <Game />
      </GameFlowProvider>
    </FeedbackProvider>
  );

describe('story main path smoke baseline', () => {
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
});
