// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { initGame, initializeStory, processGameInput } from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import { useStoryTurnSubmission } from './useStoryTurnSubmission';

vi.mock('@/services/gameApi', () => ({
  initGame: vi.fn(),
  initializeStory: vi.fn(),
  processGameInput: vi.fn(),
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
  rollbackPendingUserMessage: vi.fn(),
  stopLoading: vi.fn(),
  enterScene: vi.fn(),
  applyCompositeScene: vi.fn(),
  applySceneVisual: vi.fn(),
  appendMessage: vi.fn(),
});

describe('useStoryTurnSubmission', () => {
  beforeEach(() => {
    vi.mocked(initGame).mockReset();
    vi.mocked(initializeStory).mockReset();
    vi.mocked(processGameInput).mockReset();
  });

  it('uses the backend returned dialogue and options when the session asks the user to reselect', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const syncActiveSession = vi.fn();
    const setCharacterImage = vi.fn();

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
      playerOptions: [{ id: 2, text: 'Retry', type: 'action' }],
      isGameFinished: false,
    });

    const { result } = renderHook(() =>
      useStoryTurnSubmission({
        feedback,
        state: {
          loading: false,
          threadId: 'thread-old',
          currentOptions: [{ id: 1, text: 'Take the risk', type: 'action' }],
          currentDialogue: 'A tense pause fills the room.',
          currentScene: 'study_room',
          characterImageUrl: '/character.png',
        },
        actions,
        preferredCharacterId: 'character-1',
        setCharacterImage,
        syncActiveSession,
      })
    );

    await act(async () => {
      await result.current.selectOption(0);
    });

    expect(syncActiveSession).toHaveBeenCalledWith('thread-restored');
    expect(actions.setDialogue).toHaveBeenCalledWith('Please choose again.');
    expect(actions.setOptions).toHaveBeenCalledWith([{ id: 2, text: 'Retry', type: 'action' }]);
    expect(actions.rollbackPendingUserMessage).toHaveBeenCalledTimes(1);
    expect(feedback.warning).toHaveBeenCalledWith(
      'Game session restored. Please choose an option again.'
    );
  });

  it('reinitializes a fresh opening state when story turn submission reports SESSION_EXPIRED', async () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();
    const syncActiveSession = vi.fn();
    const setCharacterImage = vi.fn();

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
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Fresh opening dialogue.',
      playerOptions: [{ id: 2, text: 'Restart from here', type: 'action' }],
      isGameFinished: false,
    });

    const { result } = renderHook(() =>
      useStoryTurnSubmission({
        feedback,
        state: {
          loading: false,
          threadId: 'thread-old',
          currentOptions: [{ id: 1, text: 'Take the risk', type: 'action' }],
          currentDialogue: 'A tense pause fills the room.',
          currentScene: 'study_room',
          characterImageUrl: '/character.png',
        },
        actions,
        preferredCharacterId: 'character-1',
        setCharacterImage,
        syncActiveSession,
      })
    );

    await act(async () => {
      await result.current.selectOption(0);
    });

    expect(initGame).toHaveBeenCalledWith({
      gameMode: 'solo',
      characterId: 'character-1',
    });
    expect(initializeStory).toHaveBeenCalledWith(
      'thread-new',
      'character-1',
      'study_room',
      '/character.png'
    );
    expect(syncActiveSession).toHaveBeenCalledWith('thread-new');
    expect(actions.setDialogue).toHaveBeenCalledWith('Fresh opening dialogue.');
    expect(actions.setOptions).toHaveBeenCalledWith([
      { id: 2, text: 'Restart from here', type: 'action' },
    ]);
    expect(feedback.success).toHaveBeenCalledWith(
      'Game session restored with a fresh story state.'
    );
  });
});
