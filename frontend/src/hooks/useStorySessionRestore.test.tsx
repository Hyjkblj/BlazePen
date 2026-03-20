// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCharacterImages } from '@/services/characterApi';
import { getStorySessionSnapshot } from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import { persistStoryProgress, readStoryThreadSave } from '@/storage/storySessionCache';
import type { CharacterData, GameSessionSnapshot, InitialGameData } from '@/types/game';
import { useStorySessionRestore } from './useStorySessionRestore';

vi.mock('@/services/characterApi', () => ({
  getCharacterImages: vi.fn(),
}));

vi.mock('@/services/gameApi', () => ({
  getStorySessionSnapshot: vi.fn(),
}));

vi.mock('@/storage/storySessionCache', () => ({
  persistStoryProgress: vi.fn(),
  readStoryThreadSave: vi.fn(),
}));

const createFeedbackSpy = () => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
});

const createActionSpies = () => ({
  replaceMessages: vi.fn(),
  startLoading: vi.fn(),
  stopLoading: vi.fn(),
  setThreadId: vi.fn(),
  setCharacterId: vi.fn(),
  setCharacterImageUrl: vi.fn(),
  setDialogue: vi.fn(),
  setOptions: vi.fn(),
  setGameFinished: vi.fn(),
  enterScene: vi.fn(),
  applyCompositeScene: vi.fn(),
  applySceneVisual: vi.fn(),
});

describe('useStorySessionRestore', () => {
  beforeEach(() => {
    vi.mocked(getCharacterImages).mockReset();
    vi.mocked(getStorySessionSnapshot).mockReset();
    vi.mocked(persistStoryProgress).mockReset();
    vi.mocked(readStoryThreadSave).mockReset();
  });

  it('falls back to the local story save when server snapshot restore fails', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const snapshot: GameSessionSnapshot = {
      currentDialogue: 'Saved dialogue',
      currentOptions: [{ id: 1, text: 'Retry', type: 'action' }],
      currentScene: null,
      sceneImageUrl: '/scene.png',
      characterImageUrl: '/character.png',
      compositeImageUrl: null,
      shouldUseComposite: false,
      isGameFinished: false,
    };

    vi.mocked(getStorySessionSnapshot).mockRejectedValueOnce(
      new ServiceError({
        code: 'REQUEST_TIMEOUT',
        message: 'Story session restore timed out.',
      })
    );
    vi.mocked(readStoryThreadSave).mockReturnValueOnce({
      threadId: 'thread-1',
      characterId: 'character-1',
      messages: [{ role: 'assistant', content: 'Saved dialogue' }],
      snapshot,
      timestamp: 1,
    });

    const { result } = renderHook(() =>
      useStorySessionRestore({
        actions,
        feedback,
        characterDraft: null,
      })
    );

    let restoreResult = null;
    await act(async () => {
      restoreResult = await result.current.restoreFromServerSnapshot('thread-1', 'character-1');
    });

    expect(restoreResult).toEqual({
      restored: true,
      source: 'local',
      error: expect.any(ServiceError),
    });
    expect(actions.replaceMessages).toHaveBeenCalledWith([
      { role: 'assistant', content: 'Saved dialogue' },
    ]);
    expect(actions.setDialogue).toHaveBeenCalledWith('Saved dialogue');
    expect(actions.setOptions).toHaveBeenCalledWith([{ id: 1, text: 'Retry', type: 'action' }]);
    expect(actions.setGameFinished).toHaveBeenCalledWith(false);
    expect(actions.applySceneVisual).toHaveBeenCalledWith({
      sceneImageUrl: '/scene.png',
      characterImageUrl: '/character.png',
      clearCharacterImage: false,
    });
  });

  it('does not treat a server-declared expired session as a local fallback candidate', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();

    vi.mocked(getStorySessionSnapshot).mockRejectedValueOnce(
      new ServiceError({
        code: 'STORY_SESSION_EXPIRED',
        message: 'Story session expired.',
      })
    );
    vi.mocked(readStoryThreadSave).mockReturnValueOnce({
      threadId: 'thread-dead',
      characterId: 'character-1',
      messages: [{ role: 'assistant', content: 'Stale dialogue' }],
      snapshot: {
        currentDialogue: 'Stale dialogue',
        currentOptions: [{ id: 1, text: 'Retry', type: 'action' }],
        currentScene: null,
        sceneImageUrl: '/scene.png',
        characterImageUrl: '/character.png',
        compositeImageUrl: null,
        shouldUseComposite: false,
        isGameFinished: false,
      },
      timestamp: 1,
    });

    const { result } = renderHook(() =>
      useStorySessionRestore({
        actions,
        feedback,
        characterDraft: null,
      })
    );

    let restoreResult = null;
    await act(async () => {
      restoreResult = await result.current.restoreFromServerSnapshot('thread-dead', 'character-1');
    });

    expect(restoreResult).toEqual({
      restored: false,
      source: 'none',
      error: expect.any(ServiceError),
    });
    expect(actions.replaceMessages).not.toHaveBeenCalled();
    expect(actions.setDialogue).not.toHaveBeenCalled();
    expect(actions.setOptions).not.toHaveBeenCalled();
  });

  it('applies initial entry data without duplicating restore logic in useGameInit', () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const characterDraft: CharacterData = {
      characterId: 'character-1',
      imageUrl: '/draft-character.png',
    };
    const initialGameData: InitialGameData = {
      sceneId: null,
      storyBackground: 'Opening background',
      characterDialogue: 'Opening dialogue',
      playerOptions: [],
      compositeImageUrl: null,
      sceneImageUrl: null,
      isGameFinished: false,
    };

    const { result } = renderHook(() =>
      useStorySessionRestore({
        actions,
        feedback,
        characterDraft,
      })
    );

    act(() => {
      result.current.applyInitialEntryData(initialGameData, {
        characterId: 'character-1',
        selectedSceneTransition: {
          sceneId: 'school_gate',
          sceneName: 'School Gate',
        },
      });
    });

    expect(actions.enterScene).toHaveBeenCalledWith('school_gate', 'School Gate', 'reset');
    expect(actions.replaceMessages).toHaveBeenCalledWith([
      { role: 'assistant', content: 'Opening background' },
      { role: 'assistant', content: 'Opening dialogue' },
    ]);
    expect(actions.setCharacterImageUrl).toHaveBeenCalledWith('/draft-character.png');
  });
});
