// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { persistStoryProgress, readStoryThreadSave } from '@/storage/storySessionCache';
import type { GameSessionSnapshot } from '@/types/game';
import { useStorySessionSnapshotCache } from './useStorySessionSnapshotCache';

vi.mock('@/storage/storySessionCache', () => ({
  persistStoryProgress: vi.fn(),
  readStoryThreadSave: vi.fn(),
}));

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

const createFeedbackSpy = () => ({
  success: vi.fn(),
  error: vi.fn(),
});

describe('useStorySessionSnapshotCache', () => {
  beforeEach(() => {
    vi.mocked(readStoryThreadSave).mockReset();
    vi.mocked(persistStoryProgress).mockReset();
  });

  it('restores local save messages and snapshot state when loadGameSave is triggered', () => {
    const actions = createActionSpies();
    const feedback = createFeedbackSpy();
    const setCharacterImage = vi.fn();
    const snapshot: GameSessionSnapshot = {
      currentDialogue: 'Saved dialogue',
      currentOptions: [{ id: 1, text: 'Retry', type: 'action' }],
      currentScene: 'study_room',
      sceneImageUrl: '/scene.png',
      characterImageUrl: '/character.png',
      compositeImageUrl: null,
      shouldUseComposite: false,
      isGameFinished: false,
    };

    vi.mocked(readStoryThreadSave).mockReturnValueOnce({
      threadId: 'thread-1',
      characterId: 'character-1',
      messages: [{ role: 'assistant', content: 'Saved dialogue' }],
      snapshot,
      timestamp: 1,
    });

    const { result } = renderHook(() =>
      useStorySessionSnapshotCache({
        actions,
        feedback,
        setCharacterImage,
      })
    );

    let restored = false;
    act(() => {
      restored = result.current.loadGameSave('thread-1');
    });

    expect(restored).toBe(true);
    expect(actions.replaceMessages).toHaveBeenCalledWith([
      { role: 'assistant', content: 'Saved dialogue' },
    ]);
    expect(actions.setDialogue).toHaveBeenCalledWith('Saved dialogue');
    expect(actions.setOptions).toHaveBeenCalledWith([{ id: 1, text: 'Retry', type: 'action' }]);
    expect(actions.enterScene).toHaveBeenCalledWith('study_room', expect.any(String));
    expect(actions.applySceneVisual).toHaveBeenCalledWith({
      sceneImageUrl: '/scene.png',
      characterImageUrl: '/character.png',
      clearCharacterImage: false,
    });
    expect(feedback.success).toHaveBeenCalledWith('Save loaded.');
  });

  it('returns false without side effects when no local save exists', () => {
    const actions = createActionSpies();
    const feedback = createFeedbackSpy();
    const setCharacterImage = vi.fn();

    vi.mocked(readStoryThreadSave).mockReturnValueOnce(null);

    const { result } = renderHook(() =>
      useStorySessionSnapshotCache({
        actions,
        feedback,
        setCharacterImage,
      })
    );

    let restored = true;
    act(() => {
      restored = result.current.restoreLocalSave('thread-missing');
    });

    expect(restored).toBe(false);
    expect(actions.replaceMessages).not.toHaveBeenCalled();
    expect(feedback.success).not.toHaveBeenCalled();
    expect(feedback.error).not.toHaveBeenCalled();
  });

  it('persists story progress through storage when saveGameProgress is called', () => {
    const actions = createActionSpies();
    const feedback = createFeedbackSpy();
    const setCharacterImage = vi.fn();

    const { result } = renderHook(() =>
      useStorySessionSnapshotCache({
        actions,
        feedback,
        setCharacterImage,
      })
    );

    const snapshot: GameSessionSnapshot = {
      currentDialogue: 'Current dialogue',
      currentOptions: [],
      currentScene: null,
      sceneImageUrl: null,
      characterImageUrl: null,
      compositeImageUrl: null,
      shouldUseComposite: false,
      isGameFinished: false,
    };

    act(() => {
      result.current.saveGameProgress(
        'thread-2',
        [{ role: 'assistant', content: 'Current dialogue' }],
        'character-2',
        snapshot
      );
    });

    expect(vi.mocked(persistStoryProgress)).toHaveBeenCalledWith({
      threadId: 'thread-2',
      characterId: 'character-2',
      messages: [{ role: 'assistant', content: 'Current dialogue' }],
      snapshot,
    });
  });
});
