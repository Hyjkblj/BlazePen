// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import { GAME_STORAGE_KEYS } from '@/storage/gameStorage';
import {
  getStorySessionHistory,
  getStorySessionSnapshot,
  getStoryEndingSummary,
  processGameInput,
} from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import Game from './Game';

vi.mock('@/services/gameApi', () => ({
  getStorySessionSnapshot: vi.fn(),
  getStorySessionHistory: vi.fn(),
  getStoryEndingSummary: vi.fn(),
  processGameInput: vi.fn(),
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
  isGameFinished = false,
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
  isGameFinished?: boolean;
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
        isGameFinished,
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
    isGameFinished: save.snapshot.isGameFinished === true,
    roundNo: 1,
    status: save.snapshot.isGameFinished === true ? 'completed' : 'in_progress',
    updatedAt: '2026-03-19T12:00:00Z',
    expiresAt: '2026-03-19T12:30:00Z',
  };
};

describe('Game page integration', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.mocked(getStorySessionSnapshot).mockReset();
    vi.mocked(getStorySessionHistory).mockReset();
    vi.mocked(processGameInput).mockReset();
    vi.mocked(getStoryEndingSummary).mockReset();
    vi.mocked(getStorySessionSnapshot).mockRejectedValue(
      new ServiceError({
        code: 'SERVICE_UNAVAILABLE',
        message: 'Snapshot unavailable.',
      })
    );
    vi.mocked(getStoryEndingSummary).mockResolvedValue({
      threadId: 'thread-default',
      status: 'in_progress',
      roundNo: 0,
      hasEnding: false,
      ending: null,
      updatedAt: null,
      expiresAt: null,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('falls back to readable local context and clears the active thread when the submitted story session is expired', async () => {
    seedSavedGame();
    seedCharacterDraft();
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-old')
    );
    vi.mocked(processGameInput).mockRejectedValueOnce(
      new ServiceError({
        code: 'STORY_SESSION_EXPIRED',
        message: 'Story session expired.',
      })
    );

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
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBeNull();
    });

    expect(screen.getByText('A tense pause fills the room.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Take the risk' })).toBeNull();
    expect(
      screen.getByText('当前为本地只读快照，无法继续提交。请稍后重试恢复或重新开始故事。')
    ).toBeTruthy();

    await waitFor(() => {
      expect(readStoredSave('gameSave_thread-old')?.messages).toEqual([
        { role: 'assistant', content: 'A tense pause fills the room.' },
      ]);
      expect(
        readStoredSave('gameSave_thread-old')?.messages.some(
          (message: { role: string; content: string }) =>
            message.role === 'user' && message.content === 'Take the risk'
        )
      ).toBe(false);
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

    await waitFor(() => {
      expect(readStoredSave('gameSave_thread-restored')?.messages).toEqual([
        { role: 'assistant', content: 'A tense pause fills the room.' },
      ]);
      expect(readStoredSave('gameSave_thread-restored')?.lastMessage).toBe(
        'A tense pause fills the room.'
      );
      expect(
        readStoredSave('gameSave_thread-restored')?.messages.some(
          (message: { role: string; content: string }) =>
            message.role === 'user' && message.content === 'Take the risk'
        )
      ).toBe(false);
      expect(readStoredSave(GAME_STORAGE_KEYS.MAIN_SAVE)?.threadId).toBe('thread-restored');
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
        code: 'STORY_SESSION_EXPIRED',
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

  it('does not reactivate persisted initial game data after the server rejects the active thread restore', async () => {
    seedSavedGame({
      threadId: 'thread-invalid',
      currentDialogue: 'Cached dialogue',
      currentOptions: [{ id: 1, text: 'Cached option', type: 'action' }],
    });
    sessionStorage.setItem(
      GAME_STORAGE_KEYS.INITIAL_GAME_DATA,
      JSON.stringify({
        sceneId: 'study_room',
        storyBackground: 'Draft opening background',
        characterDialogue: 'Draft opening dialogue',
        playerOptions: [{ id: 1, text: 'Draft option', type: 'action' }],
        compositeImageUrl: null,
        sceneImageUrl: '/draft-scene.png',
        isGameFinished: false,
      })
    );
    vi.mocked(getStorySessionSnapshot).mockRejectedValueOnce(
      new ServiceError({
        code: 'STORY_SESSION_NOT_FOUND',
        message: 'Story session not found.',
      })
    );

    renderGamePage();

    await waitFor(() => {
      expect(getStorySessionSnapshot).toHaveBeenCalledWith('thread-invalid');
    });

    await waitFor(() => {
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBeNull();
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.INITIAL_GAME_DATA)).toBeNull();
    });

    expect(screen.queryByText('Draft opening background')).toBeNull();
    expect(screen.queryByText('Draft opening dialogue')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Draft option' })).toBeNull();
  });

  it('falls back to readable local context and disables further submission when turn recovery fails explicitly', async () => {
    seedSavedGame({
      threadId: 'thread-broken',
      currentDialogue: 'Recovery failed dialogue',
      currentOptions: [{ id: 1, text: 'Unavailable option', type: 'action' }],
    });
    seedCharacterDraft();
    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce(
      buildServerSnapshotFromThreadSave('thread-broken')
    );
    vi.mocked(processGameInput).mockRejectedValueOnce(
      new ServiceError({
        code: 'STORY_SESSION_RESTORE_FAILED',
        message: 'Story session recovery failed.',
      })
    );

    renderGamePage();

    const optionButton = await screen.findByRole('button', { name: 'Unavailable option' });
    fireEvent.click(optionButton);

    await waitFor(() => {
      expect(processGameInput).toHaveBeenCalledWith({
        threadId: 'thread-broken',
        userInput: 'option:1',
        characterId: 'character-1',
      });
    });

    await waitFor(() => {
      expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBeNull();
    });

    expect(screen.getByText('Recovery failed dialogue')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Unavailable option' })).toBeNull();
    expect(
      screen.getByText('当前为本地只读快照，无法继续提交。请稍后重试恢复或重新开始故事。')
    ).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '当前记录' }));

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: '当前设备会话记录' })).toBeTruthy();
      expect(screen.getAllByText('Recovery failed dialogue').length).toBeGreaterThan(1);
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

  it('shows the current-device transcript viewer for a local read-only restore snapshot', async () => {
    seedSavedGame({
      currentDialogue: 'Saved dialogue',
      currentOptions: [{ id: 1, text: 'Retry later', type: 'action' }],
    });
    seedCharacterDraft();

    renderGamePage();

    await waitFor(() => {
      expect(screen.getByText('Saved dialogue')).toBeTruthy();
    });

    expect(
      screen.getByText('当前为本地只读快照，无法继续提交。请稍后重试恢复或重新开始故事。')
    ).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Retry later' }).hasAttribute('disabled')
    ).toBe(true);
    expect(screen.getByRole('button', { name: '服务端历史' }).hasAttribute('disabled')).toBe(
      true
    );

    fireEvent.click(screen.getByRole('button', { name: '当前记录' }));

    await waitFor(() => {
      expect(
        screen.getByRole('dialog', { name: '当前设备会话记录' })
      ).toBeTruthy();
    });

    expect(
      screen.getByText('这里只展示当前设备已经加载过的会话内容，用于恢复和回看，不代表服务端完整历史。')
    ).toBeTruthy();
    expect(screen.getAllByText('Saved dialogue').length).toBeGreaterThan(1);
  });

  it('loads persisted server history separately from the current-device transcript', async () => {
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-history');
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-1');
    sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, 'character-1');

    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce({
      threadId: 'thread-history',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: 'Recovered background',
      characterDialogue: 'Recovered dialogue',
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
      isGameFinished: false,
      roundNo: 2,
      status: 'in_progress',
      updatedAt: '2026-03-20T12:00:00Z',
      expiresAt: '2026-03-20T12:30:00Z',
    });
    vi.mocked(getStorySessionHistory).mockResolvedValueOnce({
      threadId: 'thread-history',
      status: 'in_progress',
      currentRoundNo: 2,
      latestSceneId: 'study_room',
      updatedAt: '2026-03-20T12:00:00Z',
      expiresAt: '2026-03-20T12:30:00Z',
      history: [
        {
          roundNo: 1,
          status: 'in_progress',
          sceneId: 'study_room',
          eventTitle: 'First Meeting',
          characterDialogue: 'Nice to meet you.',
          userAction: {
            kind: 'option',
            summary: 'Wave back',
            rawInput: null,
            optionIndex: 0,
            optionText: 'Wave back',
            optionType: 'action',
          },
          stateSummary: {
            changes: {
              trust: 10,
            },
            currentStates: {
              trust: 60,
            },
          },
          isEventFinished: false,
          isGameFinished: false,
          createdAt: '2026-03-20T11:58:00Z',
        },
      ],
    });

    renderGamePage();

    await waitFor(() => {
      expect(screen.getByText('Recovered dialogue')).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: '服务端历史' }));

    await waitFor(() => {
      expect(getStorySessionHistory).toHaveBeenCalledWith('thread-history');
    });

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: '服务端历史' })).toBeTruthy();
      expect(screen.getByText('First Meeting · 自习室')).toBeTruthy();
      expect(screen.getByText('Wave back')).toBeTruthy();
      expect(screen.getByText('Nice to meet you.')).toBeTruthy();
      expect(screen.getByText('信任 +10')).toBeTruthy();
    });
  });

  it('loads and reopens the ending summary when a finished story session is restored', async () => {
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-finished');
    sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-1');
    sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, 'character-1');

    vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce({
      threadId: 'thread-finished',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'cafe_nearby',
      sceneImageUrl: '/ending-scene.png',
      compositeImageUrl: null,
      storyBackground: 'Ending background',
      characterDialogue: 'This is where our story settles.',
      playerOptions: [],
      isGameFinished: true,
      roundNo: 6,
      status: 'completed',
      updatedAt: '2026-03-19T14:00:00Z',
      expiresAt: '2026-03-19T14:30:00Z',
    });
    vi.mocked(getStoryEndingSummary).mockResolvedValueOnce({
      threadId: 'thread-finished',
      status: 'completed',
      roundNo: 6,
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm, hopeful ending.',
        sceneId: 'cafe_nearby',
        eventTitle: 'Final Promise',
        keyStates: {
          favorability: 88,
          trust: 76,
          hostility: 12,
          dependence: null,
        },
      },
      updatedAt: '2026-03-19T14:00:00Z',
      expiresAt: '2026-03-19T14:30:00Z',
    });

    renderGamePage();

    await waitFor(() => {
      expect(getStoryEndingSummary).toHaveBeenCalledWith('thread-finished');
    });

    await waitFor(() => {
      expect(screen.getByText('圆满结局')).toBeTruthy();
      expect(screen.getByText('Final Promise · 咖啡厅')).toBeTruthy();
      expect(screen.getByText('A warm, hopeful ending.')).toBeTruthy();
      expect(screen.getByText('88')).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: '关闭' }));

    await waitFor(() => {
      expect(screen.queryByText('圆满结局')).toBeNull();
    });

    fireEvent.click(screen.getByRole('button', { name: '结局摘要' }));

    await waitFor(() => {
      expect(screen.getByText('圆满结局')).toBeTruthy();
    });
  });

  it.each([
    {
      status: 404,
      code: 'STORY_SESSION_NOT_FOUND' as const,
    },
    {
      status: 410,
      code: 'SESSION_EXPIRED' as const,
    },
    {
      status: 500,
      code: 'SERVICE_UNAVAILABLE' as const,
    },
  ])(
    'shows ending error state and allows retry when the restored ending summary request fails with status $status',
    async ({ status, code }) => {
      sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-finished');
      sessionStorage.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-1');
      sessionStorage.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, 'character-1');

      vi.mocked(getStorySessionSnapshot).mockResolvedValueOnce({
        threadId: 'thread-finished',
        sessionRestored: false,
        needReselectOption: false,
        restoredFromThreadId: null,
        sceneId: 'cafe_nearby',
        sceneImageUrl: '/ending-scene.png',
        compositeImageUrl: null,
        storyBackground: 'Ending background',
        characterDialogue: 'This is where our story settles.',
        playerOptions: [],
        isGameFinished: true,
        roundNo: 6,
        status: 'completed',
        updatedAt: '2026-03-19T14:00:00Z',
        expiresAt: '2026-03-19T14:30:00Z',
      });
      vi.mocked(getStoryEndingSummary)
        .mockRejectedValueOnce(
          new ServiceError({
            code,
            status,
            message: `Ending summary unavailable (${status}).`,
          })
        )
        .mockResolvedValueOnce({
          threadId: 'thread-finished',
          status: 'completed',
          roundNo: 6,
          hasEnding: true,
          ending: {
            type: 'good_ending',
            description: 'Recovered ending summary.',
            sceneId: 'cafe_nearby',
            eventTitle: 'Final Promise',
            keyStates: {
              favorability: 88,
              trust: 76,
              hostility: 12,
              dependence: null,
            },
          },
          updatedAt: '2026-03-19T14:00:00Z',
          expiresAt: '2026-03-19T14:30:00Z',
        });

      renderGamePage();

      await waitFor(() => {
        expect(getStoryEndingSummary).toHaveBeenCalledTimes(1);
        expect(getStoryEndingSummary).toHaveBeenCalledWith('thread-finished');
      });

      const errorDialog = await screen.findByRole('dialog', { name: '故事结局' });
      expect(within(errorDialog).getByText(`Ending summary unavailable (${status}).`)).toBeTruthy();

      const actionButtons = within(errorDialog)
        .getAllByRole('button')
        .filter((button) => (button.textContent ?? '').trim() !== '');
      fireEvent.click(actionButtons[0]);

      await waitFor(() => {
        expect(getStoryEndingSummary).toHaveBeenCalledTimes(2);
      });

      const retriedDialog = await screen.findByRole('dialog', { name: '故事结局' });
      await waitFor(() => {
        expect(within(retriedDialog).getByText('Recovered ending summary.')).toBeTruthy();
        expect(
          within(retriedDialog).queryByText(`Ending summary unavailable (${status}).`)
        ).toBeNull();
      });
    }
  );
});
