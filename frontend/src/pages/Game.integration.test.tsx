// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import { GAME_STORAGE_KEYS } from '@/storage/gameStorage';
import {
  getStorySessionSnapshot,
  initGame,
  initializeStory,
  processGameInput,
} from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import Game from './Game';

vi.mock('@/services/gameApi', () => ({
  initGame: vi.fn(),
  initializeStory: vi.fn(),
  getStorySessionSnapshot: vi.fn(),
  processGameInput: vi.fn(),
  checkEnding: vi.fn(),
  triggerEnding: vi.fn(),
}));

vi.mock('@/hooks', async () => {
  const actual = await vi.importActual<typeof import('@/hooks')>('@/hooks');
  return {
    ...actual,
    useGameTts: vi.fn(),
  };
});

const seedSavedGame = ({
  threadId = 'thread-old',
  characterId = 'character-1',
  currentDialogue = 'A tense pause fills the room.',
  currentOptions = [{ id: 1, text: 'Take the risk', type: 'action' }],
  currentScene = 'study_room',
  sceneImageUrl = '/scene.png',
  characterImageUrl = '/character.png',
  compositeImageUrl = null,
  shouldUseComposite = false,
}: {
  threadId?: string;
  characterId?: string;
  currentDialogue?: string;
  currentOptions?: Array<{ id: number; text: string; type: string }>;
  currentScene?: string | null;
  sceneImageUrl?: string | null;
  characterImageUrl?: string | null;
  compositeImageUrl?: string | null;
  shouldUseComposite?: boolean;
} = {}) => {
  sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, threadId);
  sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, characterId);
  sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, characterId);

  localStorage.setItem(
    `gameSave_${threadId}`,
    JSON.stringify({
      threadId,
      characterId,
      messages: [{ role: 'assistant', content: currentDialogue }],
      snapshot: {
        currentDialogue,
        currentOptions,
        currentScene,
        sceneImageUrl,
        characterImageUrl,
        compositeImageUrl,
        shouldUseComposite,
      },
      timestamp: 1,
    })
  );
};

const seedCharacterDraft = ({
  characterId = 'character-1',
  imageUrl = '/character.png',
}: {
  characterId?: string;
  imageUrl?: string;
} = {}) => {
  sessionStorage.setItem(
    GAME_STORAGE_KEYS.CHARACTER_DATA,
    JSON.stringify({
      characterId,
      imageUrl,
    })
  );
};

const renderGamePage = () =>
  render(
    <FeedbackProvider>
      <GameFlowProvider>
        <Game />
      </GameFlowProvider>
    </FeedbackProvider>
  );

const readStoredSave = (key: string) => {
  const raw = localStorage.getItem(key);
  return raw ? JSON.parse(raw) : null;
};

const buildServerSnapshotFromThreadSave = (threadId: string) => {
  const save = readStoredSave(`gameSave_${threadId}`);
  if (!save?.snapshot) {
    throw new Error(`Expected a saved story snapshot for thread ${threadId}.`);
  }

  return {
    threadId,
    sessionRestored: false,
    needReselectOption: false,
    restoredFromThreadId: null,
    sceneId: save.snapshot.currentScene,
    sceneImageUrl: save.snapshot.sceneImageUrl,
    compositeImageUrl: save.snapshot.compositeImageUrl,
    storyBackground: null,
    characterDialogue: save.snapshot.currentDialogue,
    playerOptions: save.snapshot.currentOptions,
    isGameFinished: false,
    roundNo: 1,
    status: 'in_progress',
    updatedAt: '2026-03-19T12:00:00Z',
    expiresAt: '2026-03-19T12:30:00Z',
  };
};

describe('Game page integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.mocked(initGame).mockReset();
    vi.mocked(initializeStory).mockReset();
    vi.mocked(getStorySessionSnapshot).mockReset();
    vi.mocked(processGameInput).mockReset();
    vi.mocked(getStorySessionSnapshot).mockRejectedValue(
      new ServiceError({
        code: 'SERVICE_UNAVAILABLE',
        message: 'Snapshot unavailable.',
      })
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('recovers an expired session by loading a fresh opening state for the new thread', async () => {
    seedSavedGame();
    seedCharacterDraft();
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-old')
    );
    vi.mocked(processGameInput).mockRejectedValueOnce(
      new ServiceError({
        code: 'SESSION_EXPIRED',
        message: 'Story session expired.',
      })
    );
    vi.mocked(initGame).mockResolvedValueOnce({
      threadId: 'thread-new',
      userId: null,
      gameMode: 'solo',
    });
    vi.mocked(initializeStory).mockResolvedValueOnce({
      sceneId: 'study_room',
      sceneImageUrl: '/scene-recovered.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Fresh opening after recovery',
      playerOptions: [{ id: 2, text: 'Restart from here', type: 'action' }],
      isGameFinished: false,
    });

    renderGamePage();

    const optionButton = await screen.findByRole('button', { name: 'Take the risk' });
    fireEvent.click(optionButton);

    await waitFor(() => {
      expect(processGameInput).toHaveBeenCalledWith({
        threadId: 'thread-old',
        userInput: 'option:1',
        characterId: 'character-1',
      });
    });

    await waitFor(() => {
      expect(initGame).toHaveBeenCalledWith({
        gameMode: 'solo',
        characterId: 'character-1',
      });
    });

    await waitFor(() => {
      expect(initializeStory).toHaveBeenCalledWith(
        'thread-new',
        'character-1',
        'study_room',
        '/character.png'
      );
    });

    await waitFor(() => {
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBe('thread-new');
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID)).toBe('character-1');
    });

    await waitFor(() => {
      expect(screen.getByText('Fresh opening after recovery')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Restart from here' })).toBeTruthy();
    });
  });

  it('uses the backend returned option list when the restored session requires reselecting the option', async () => {
    seedSavedGame();
    seedCharacterDraft();
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-old')
    );
    vi.mocked(processGameInput).mockResolvedValueOnce({
      threadId: 'thread-restored',
      sessionRestored: true,
      needReselectOption: true,
      restoredFromThreadId: 'thread-old',
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Please choose again.',
      playerOptions: [{ id: 1, text: 'Retry', type: 'action' }],
      isGameFinished: false,
    });

    renderGamePage();

    const optionButton = await screen.findByRole('button', { name: 'Take the risk' });
    fireEvent.click(optionButton);

    await waitFor(() => {
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBe('thread-restored');
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID)).toBe('character-1');
    });

    await waitFor(() => {
      expect(screen.getByText('Please choose again.')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Retry' })).toBeTruthy();
      expect(screen.queryByRole('button', { name: 'Take the risk' })).toBeNull();
    });
  });

  it('does not restore a stale local snapshot when the server explicitly marks the story session expired', async () => {
    seedSavedGame({
      threadId: 'thread-dead',
      currentDialogue: 'Stale dialogue',
      currentOptions: [{ id: 1, text: 'Retry stale path', type: 'action' }],
    });
    vi.mocked(getStorySessionSnapshot).mockRejectedValueOnce(
      new ServiceError({
        code: 'SESSION_EXPIRED',
        message: 'Story session expired.',
      })
    );

    renderGamePage();

    await waitFor(() => {
      expect(getStorySessionSnapshot).toHaveBeenCalledWith('thread-dead');
    });

    await waitFor(() => {
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBeNull();
    });

    expect(screen.queryByText('Stale dialogue')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Retry stale path' })).toBeNull();
  });

  it('persists composite asset fallback state and keeps the broken url out of restored snapshots', async () => {
    seedSavedGame({
      currentOptions: [],
      sceneImageUrl: null,
      characterImageUrl: null,
      compositeImageUrl: '/broken-composite.png',
      shouldUseComposite: true,
    });
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-old')
    );

    const { container, unmount } = renderGamePage();

    await waitFor(() => {
      expect(container.querySelector('.composite-scene-image')).toBeTruthy();
    });

    const compositeImage = container.querySelector('.composite-scene-image');
    if (!(compositeImage instanceof HTMLImageElement)) {
      throw new Error('Expected composite image to render before simulating an asset failure.');
    }

    fireEvent.error(compositeImage);

    await waitFor(() => {
      expect(container.querySelector('.composite-scene-image')).toBeNull();
    });

    await waitFor(() => {
      const alerts = container.querySelectorAll('[role="alert"]');
      expect(alerts.length).toBe(1);
    });

    const placeholder = container.querySelector('.scene-placeholder-fallback');
    expect(placeholder?.getAttribute('style') ?? '').toContain('display: flex');

    await waitFor(() => {
      expect(readStoredSave('gameSave_thread-old')?.snapshot).toMatchObject({
        compositeImageUrl: null,
        shouldUseComposite: false,
      });
      expect(readStoredSave(GAME_STORAGE_KEYS.MAIN_SAVE)?.snapshot).toMatchObject({
        compositeImageUrl: null,
        shouldUseComposite: false,
      });
    });

    unmount();
    const remounted = renderGamePage();
    await waitFor(() => {
      expect(remounted.container.querySelector('.composite-scene-image')).toBeNull();
    });
  });

  it('persists character asset fallback state so restored sessions keep the character layer hidden', async () => {
    seedSavedGame({
      currentOptions: [],
      sceneImageUrl: '/scene.png',
      characterImageUrl: '/broken-character.png',
      compositeImageUrl: null,
      shouldUseComposite: false,
    });
    seedCharacterDraft({
      imageUrl: '/broken-character.png',
    });
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-old')
    );

    const { container, unmount } = renderGamePage();

    await waitFor(() => {
      expect(container.querySelector('.character-overlay-image')).toBeTruthy();
    });

    const characterImage = container.querySelector('.character-overlay-image');
    if (!(characterImage instanceof HTMLImageElement)) {
      throw new Error('Expected character image to render before simulating an asset failure.');
    }

    fireEvent.error(characterImage);

    await waitFor(() => {
      expect(container.querySelector('.character-overlay-image')).toBeNull();
    });

    await waitFor(() => {
      expect(readStoredSave('gameSave_thread-old')?.snapshot).toMatchObject({
        characterImageUrl: null,
      });
      expect(readStoredSave(GAME_STORAGE_KEYS.MAIN_SAVE)?.snapshot).toMatchObject({
        characterImageUrl: null,
      });
    });

    unmount();
    const remounted = renderGamePage();
    await waitFor(() => {
      expect(remounted.container.querySelector('.character-overlay-image')).toBeNull();
    });
  });

  it('persists scene asset fallback state so restored sessions keep the broken background cleared', async () => {
    seedSavedGame({
      currentOptions: [],
      sceneImageUrl: '/broken-scene.png',
      characterImageUrl: '/character.png',
      compositeImageUrl: null,
      shouldUseComposite: false,
    });
    seedCharacterDraft();
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-old')
    );

    const { container, unmount } = renderGamePage();

    await waitFor(() => {
      expect(container.querySelector('.scene-background-image')).toBeTruthy();
    });

    const sceneImage = container.querySelector('.scene-background-image');
    if (!(sceneImage instanceof HTMLImageElement)) {
      throw new Error('Expected scene image to render before simulating an asset failure.');
    }

    fireEvent.error(sceneImage);

    await waitFor(() => {
      expect(container.querySelector('.scene-background-image')).toBeNull();
    });

    await waitFor(() => {
      expect(readStoredSave('gameSave_thread-old')?.snapshot).toMatchObject({
        sceneImageUrl: null,
        shouldUseComposite: false,
      });
      expect(readStoredSave(GAME_STORAGE_KEYS.MAIN_SAVE)?.snapshot).toMatchObject({
        sceneImageUrl: null,
        shouldUseComposite: false,
      });
    });

    unmount();
    const remounted = renderGamePage();
    await waitFor(() => {
      expect(remounted.container.querySelector('.scene-background-image')).toBeNull();
    });
  });

  it('restores the current story state from the server snapshot when the page refreshes without a local save', async () => {
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-live');
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-1');
    sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, 'character-1');

    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce({
      threadId: 'thread-live',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'study_room',
      sceneImageUrl: null,
      compositeImageUrl: '/restored-composite.png',
      storyBackground: 'Recovered background',
      characterDialogue: 'Recovered dialogue',
      playerOptions: [{ id: 1, text: 'Resume', type: 'action' }],
      isGameFinished: false,
      roundNo: 2,
      status: 'in_progress',
      updatedAt: '2026-03-19T12:00:00Z',
      expiresAt: '2026-03-19T12:30:00Z',
    });

    renderGamePage();

    await waitFor(() => {
      expect(getStorySessionSnapshot).toHaveBeenCalledWith('thread-live');
    });

    await waitFor(() => {
      expect(screen.getByText('Recovered dialogue')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Resume' })).toBeTruthy();
    });
  });

  it('ignores a corrupted local save when the server snapshot can still restore the session', async () => {
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-live');
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-1');
    sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, 'character-1');
    localStorage.setItem('gameSave_thread-live', '{invalid-json');

    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce({
      threadId: 'thread-live',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'cafe_nearby',
      sceneImageUrl: null,
      compositeImageUrl: '/restored-cafe.png',
      storyBackground: null,
      characterDialogue: 'Recovered after corrupted cache',
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
      isGameFinished: false,
      roundNo: 4,
      status: 'in_progress',
      updatedAt: '2026-03-19T13:00:00Z',
      expiresAt: '2026-03-19T13:30:00Z',
    });

    renderGamePage();

    await waitFor(() => {
      expect(getStorySessionSnapshot).toHaveBeenCalledWith('thread-live');
    });

    await waitFor(() => {
      expect(screen.getByText('Recovered after corrupted cache')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Continue' })).toBeTruthy();
    });
  });
});
