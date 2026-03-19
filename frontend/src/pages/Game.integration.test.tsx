// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import { GAME_STORAGE_KEYS } from '@/storage/gameStorage';
import { initGame, processGameInput } from '@/services/gameApi';
import Game from './Game';

vi.mock('@/services/gameApi', () => ({
  initGame: vi.fn(),
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

describe('Game page integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.mocked(initGame).mockReset();
    vi.mocked(processGameInput).mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('recovers an expired session and restores the previous choice list for retry', async () => {
    seedSavedGame();
    vi.mocked(processGameInput).mockRejectedValueOnce({
      response: {
        data: {
          message: 'thread not found',
        },
      },
    });
    vi.mocked(initGame).mockResolvedValueOnce({ thread_id: 'thread-new' });

    renderGamePage();

    const optionButton = await screen.findByRole('button', { name: 'Take the risk' });
    fireEvent.click(optionButton);

    await waitFor(() => {
      expect(processGameInput).toHaveBeenCalledWith({
        thread_id: 'thread-old',
        user_input: 'option:1',
        character_id: 'character-1',
      });
    });

    await waitFor(() => {
      expect(initGame).toHaveBeenCalledWith({
        game_mode: 'solo',
        character_id: 'character-1',
      });
    });

    await waitFor(() => {
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBe('thread-new');
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID)).toBe('character-1');
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Take the risk' })).toBeTruthy();
    });
  });

  it('persists composite asset fallback state and keeps the broken url out of restored snapshots', async () => {
    seedSavedGame({
      currentOptions: [],
      sceneImageUrl: null,
      characterImageUrl: null,
      compositeImageUrl: '/broken-composite.png',
      shouldUseComposite: true,
    });

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
});
