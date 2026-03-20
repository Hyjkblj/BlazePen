// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import Layout from '@/components/Layout';
import { ROUTES } from '@/config/routes';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import {
  checkEnding,
  getStorySessionSnapshot,
  initGame,
  initializeStory,
  processGameInput,
} from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import { GAME_STORAGE_KEYS } from '@/storage/gameStorage';
import FirstStep from './FirstStep';
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

const ROUTE_CONFIG: RouteObject[] = [
  {
    path: ROUTES.HOME,
    element: <Layout />,
    children: [
      {
        path: ROUTES.FIRST_STEP.slice(1),
        element: <FirstStep />,
      },
      {
        path: ROUTES.GAME.slice(1),
        element: <Game />,
      },
    ],
  },
];

const seedStoryResumeSave = ({
  threadId = 'thread-resume',
  characterId = 'character-1',
  currentDialogue = 'Saved dialogue',
  currentOptions = [{ id: 1, text: 'Retry later', type: 'action' }],
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
        isGameFinished: false,
      },
      timestamp: 1,
    })
  );

  localStorage.setItem(
    GAME_STORAGE_KEYS.MAIN_SAVE,
    JSON.stringify({
      threadId,
      characterId,
      lastMessage: currentDialogue,
      snapshot: {
        currentDialogue,
        currentOptions,
        currentScene,
        sceneImageUrl,
        characterImageUrl,
        compositeImageUrl,
        shouldUseComposite,
        isGameFinished: false,
      },
      timestamp: 1,
    })
  );
};

const renderResumeFlow = () => {
  const router = createMemoryRouter(ROUTE_CONFIG, {
    initialEntries: [ROUTES.FIRST_STEP],
  });

  render(
    <FeedbackProvider>
      <GameFlowProvider>
        <RouterProvider router={router} />
      </GameFlowProvider>
    </FeedbackProvider>
  );

  return router;
};

describe('FirstStep page integration', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    sessionStorage.clear();
    localStorage.clear();
    vi.mocked(initGame).mockReset();
    vi.mocked(initializeStory).mockReset();
    vi.mocked(processGameInput).mockReset();
    vi.mocked(getStorySessionSnapshot).mockReset();
    vi.mocked(checkEnding).mockReset();
    vi.mocked(checkEnding).mockResolvedValue({
      hasEnding: false,
      ending: null,
    });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('continues to Game and falls back to the last local snapshot in read-only mode after a restore timeout', async () => {
    seedStoryResumeSave();
    vi.mocked(getStorySessionSnapshot).mockRejectedValueOnce(
      new ServiceError({
        code: 'REQUEST_TIMEOUT',
        message: 'Story session restore timed out.',
      })
    );

    const router = renderResumeFlow();

    fireEvent.click(screen.getByRole('button', { name: '继续游戏' }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    vi.useRealTimers();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe(ROUTES.GAME);
    });

    await waitFor(() => {
      expect(getStorySessionSnapshot).toHaveBeenCalledWith('thread-resume');
    });

    await waitFor(() => {
      expect(screen.getByText('Saved dialogue')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Retry later' })).toBeTruthy();
    });

    expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_THREAD_ID)).toBeNull();
    expect(sessionStorage.getItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID)).toBeNull();
    expect(sessionStorage.getItem(GAME_STORAGE_KEYS.RESTORE_THREAD_ID)).toBeNull();
    expect(processGameInput).not.toHaveBeenCalled();
    expect(initGame).not.toHaveBeenCalled();
    expect(initializeStory).not.toHaveBeenCalled();
    expect(checkEnding).not.toHaveBeenCalled();

    expect(
      screen.getByText(
        '当前为本地只读快照，无法继续提交。请稍后重试恢复或重新开始故事。'
      )
    ).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Retry later' }).hasAttribute('disabled')).toBe(
      true
    );

    fireEvent.click(screen.getByRole('button', { name: '当前记录' }));

    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: '当前设备会话记录' })).toBeTruthy();
      expect(screen.getAllByText('Saved dialogue').length).toBeGreaterThan(1);
    });
  });
});
