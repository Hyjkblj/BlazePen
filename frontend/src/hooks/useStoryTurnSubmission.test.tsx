// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { ServiceError } from '@/services/serviceError';
import { submitStoryTurn } from '@/services/storyTurnService';
import { useStoryTurnSubmission } from './useStoryTurnSubmission';

vi.mock('@/services/storyTurnService', () => ({
  submitStoryTurn: vi.fn(),
}));

const createFeedbackSpy = (): FeedbackContextValue => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  dismiss: vi.fn(),
});

const createActionSpies = () => ({
  prepareOptionSelection: vi.fn(),
  setThreadId: vi.fn(),
  setDialogue: vi.fn(),
  setOptions: vi.fn(),
  setGameFinished: vi.fn(),
  replaceMessages: vi.fn(),
  rollbackPendingUserMessage: vi.fn(),
  stopLoading: vi.fn(),
  enterScene: vi.fn(),
  applyCompositeScene: vi.fn(),
  applySceneVisual: vi.fn(),
  appendMessage: vi.fn(),
});

describe('useStoryTurnSubmission', () => {
  beforeEach(() => {
    vi.mocked(submitStoryTurn).mockReset();
  });

  it('uses the backend returned dialogue and options when the session asks the user to reselect', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const syncActiveSession = vi.fn();
    const setCharacterImage = vi.fn();
    const persistReadOnlySnapshot = vi.fn();

    vi.mocked(submitStoryTurn).mockResolvedValueOnce({
      threadId: 'thread-restored',
      sessionRestored: true,
      needReselectOption: true,
      restoredFromThreadId: 'thread-old',
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Please choose again.',
      playerOptions: [{ id: 2, text: 'Retry', type: 'action' }],
      isGameFinished: false,
    });

    const { result } = renderHook(() =>
      useStoryTurnSubmission({
        feedback,
        state: {
          messages: [{ role: 'assistant', content: 'A tense pause fills the room.' }],
          loading: false,
          threadId: 'thread-old',
          currentOptions: [{ id: 1, text: 'Take the risk', type: 'action' }],
          currentDialogue: 'A tense pause fills the room.',
          currentScene: 'study_room',
          characterImageUrl: '/character.png',
          isGameFinished: false,
        },
        actions,
        preferredCharacterId: 'character-1',
        setCharacterImage,
        syncActiveSession,
        persistReadOnlySnapshot,
      })
    );

    await act(async () => {
      await result.current.selectOption(0);
    });

    expect(syncActiveSession).toHaveBeenCalledWith('thread-restored');
    expect(actions.setDialogue).toHaveBeenCalledWith('Please choose again.');
    expect(actions.setOptions).toHaveBeenCalledWith([{ id: 2, text: 'Retry', type: 'action' }]);
    expect(actions.setGameFinished).toHaveBeenCalledWith(false);
    expect(actions.rollbackPendingUserMessage).toHaveBeenCalledTimes(1);
    expect(feedback.warning).toHaveBeenCalledWith(
      'Game session restored. Please choose an option again.'
    );
    expect(persistReadOnlySnapshot).not.toHaveBeenCalled();
  });

  it('drops the active session instead of switching to a fresh thread when the story session expires', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const syncActiveSession = vi.fn();
    const setCharacterImage = vi.fn();
    const persistReadOnlySnapshot = vi.fn();

    vi.mocked(submitStoryTurn).mockRejectedValueOnce(
      new ServiceError({
        code: 'STORY_SESSION_EXPIRED',
        message: 'Story session expired.',
      })
    );

    const { result } = renderHook(() =>
      useStoryTurnSubmission({
        feedback,
        state: {
          messages: [{ role: 'assistant', content: 'A tense pause fills the room.' }],
          loading: false,
          threadId: 'thread-old',
          currentOptions: [{ id: 1, text: 'Take the risk', type: 'action' }],
          currentDialogue: 'A tense pause fills the room.',
          currentScene: 'study_room',
          characterImageUrl: '/character.png',
          isGameFinished: false,
        },
        actions,
        preferredCharacterId: 'character-1',
        setCharacterImage,
        syncActiveSession,
        persistReadOnlySnapshot,
      })
    );

    await act(async () => {
      await result.current.selectOption(0);
    });

    expect(submitStoryTurn).toHaveBeenCalledWith({
      threadId: 'thread-old',
      userInput: 'option:1',
      characterId: 'character-1',
    });
    expect(syncActiveSession).toHaveBeenCalledWith(null);
    expect(persistReadOnlySnapshot).toHaveBeenCalledWith('thread-old', [
      { role: 'assistant', content: 'A tense pause fills the room.' },
    ]);
    expect(actions.setDialogue).toHaveBeenCalledWith('A tense pause fills the room.');
    expect(actions.setOptions).toHaveBeenLastCalledWith([]);
    expect(actions.setGameFinished).toHaveBeenCalledWith(false);
    expect(actions.rollbackPendingUserMessage).toHaveBeenCalledTimes(1);
    expect(actions.replaceMessages).not.toHaveBeenCalled();
    expect(feedback.error).toHaveBeenCalledWith('Story session expired. Please restart the story.');
  });

  it('drops the active session when the backend restore flow fails explicitly', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const syncActiveSession = vi.fn();
    const setCharacterImage = vi.fn();
    const persistReadOnlySnapshot = vi.fn();

    vi.mocked(submitStoryTurn).mockRejectedValueOnce(
      new ServiceError({
        code: 'STORY_SESSION_RESTORE_FAILED',
        message: 'Story session recovery failed.',
      })
    );

    const { result } = renderHook(() =>
      useStoryTurnSubmission({
        feedback,
        state: {
          messages: [{ role: 'assistant', content: 'A tense pause fills the room.' }],
          loading: false,
          threadId: 'thread-old',
          currentOptions: [{ id: 1, text: 'Take the risk', type: 'action' }],
          currentDialogue: 'A tense pause fills the room.',
          currentScene: 'study_room',
          characterImageUrl: '/character.png',
          isGameFinished: false,
        },
        actions,
        preferredCharacterId: 'character-1',
        setCharacterImage,
        syncActiveSession,
        persistReadOnlySnapshot,
      })
    );

    await act(async () => {
      await result.current.selectOption(0);
    });

    expect(syncActiveSession).toHaveBeenCalledWith(null);
    expect(persistReadOnlySnapshot).toHaveBeenCalledWith('thread-old', [
      { role: 'assistant', content: 'A tense pause fills the room.' },
    ]);
    expect(actions.setOptions).toHaveBeenLastCalledWith([]);
    expect(feedback.error).toHaveBeenCalledWith(
      'Game session could not be recovered. Please restart the story.'
    );
  });
});
