import { describe, expect, it, vi } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import type { GameTurnResult } from '@/types/game';
import {
  applyStoryTurnReselectState,
  applyStoryTurnResponseState,
  handleStoryTurnSubmissionError,
} from './storyTurnSubmissionExecutor';

const createResponseActions = () => ({
  setDialogue: vi.fn(),
  setOptions: vi.fn(),
  setGameFinished: vi.fn(),
  enterScene: vi.fn(),
  applyCompositeScene: vi.fn(),
  applySceneVisual: vi.fn(),
  appendMessage: vi.fn(),
});

const createReselectActions = () => ({
  rollbackPendingUserMessage: vi.fn(),
  setDialogue: vi.fn(),
  setOptions: vi.fn(),
  setGameFinished: vi.fn(),
  enterScene: vi.fn(),
  applyCompositeScene: vi.fn(),
  applySceneVisual: vi.fn(),
});

describe('storyTurnSubmissionExecutor', () => {
  it('applies normal turn response and announces finish', () => {
    const feedback = { info: vi.fn() };
    const actions = createResponseActions();
    const ensureCharacterImage = vi.fn();
    const response: GameTurnResult = {
      threadId: 'thread-1',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'cafe_nearby',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Welcome.',
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
      isGameFinished: true,
    };

    applyStoryTurnResponseState({
      response,
      currentScene: 'study_room',
      ensureCharacterImage,
      feedback,
      actions,
    });

    expect(actions.enterScene).toHaveBeenCalledWith(
      'cafe_nearby',
      expect.any(String),
      'advance'
    );
    expect(actions.applySceneVisual).toHaveBeenCalledWith({
      sceneImageUrl: '/scene.png',
    });
    expect(ensureCharacterImage).toHaveBeenCalledTimes(1);
    expect(actions.setDialogue).toHaveBeenCalledWith('Welcome.');
    expect(actions.appendMessage).toHaveBeenCalledWith({
      role: 'assistant',
      content: 'Welcome.',
    });
    expect(actions.setOptions).toHaveBeenCalledWith([{ id: 1, text: 'Continue', type: 'action' }]);
    expect(actions.setGameFinished).toHaveBeenCalledWith(true);
    expect(feedback.info).toHaveBeenCalledWith('Story finished.');
  });

  it('applies reselect response without appending assistant message', () => {
    const actions = createReselectActions();
    const ensureCharacterImage = vi.fn();
    const response: GameTurnResult = {
      threadId: 'thread-2',
      sessionRestored: true,
      needReselectOption: true,
      restoredFromThreadId: 'thread-1',
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Please choose again.',
      playerOptions: [{ id: 2, text: 'Retry', type: 'action' }],
      isGameFinished: false,
    };

    applyStoryTurnReselectState({
      response,
      currentScene: 'study_room',
      ensureCharacterImage,
      actions,
    });

    expect(actions.rollbackPendingUserMessage).toHaveBeenCalledTimes(1);
    expect(actions.setDialogue).toHaveBeenCalledWith('Please choose again.');
    expect(actions.setOptions).toHaveBeenCalledWith([{ id: 2, text: 'Retry', type: 'action' }]);
    expect(actions.setGameFinished).toHaveBeenCalledWith(false);
    expect(actions.enterScene).not.toHaveBeenCalled();
  });

  it('handles unrecoverable session errors by entering read-only mode', () => {
    const feedback = { error: vi.fn() };
    const actions = { setOptions: vi.fn() };
    const restorePreviousTurnState = vi.fn();
    const syncActiveSession = vi.fn();
    const persistReadOnlySnapshot = vi.fn();
    const error = new ServiceError({
      code: 'STORY_SESSION_EXPIRED',
      message: 'Story session expired.',
    });

    handleStoryTurnSubmissionError({
      error,
      threadId: 'thread-3',
      messages: [{ role: 'assistant', content: 'Saved dialogue' }],
      feedback,
      actions,
      restorePreviousTurnState,
      syncActiveSession,
      persistReadOnlySnapshot,
    });

    expect(feedback.error).toHaveBeenCalledWith('Story session expired. Please restart the story.');
    expect(persistReadOnlySnapshot).toHaveBeenCalledWith('thread-3', [
      { role: 'assistant', content: 'Saved dialogue' },
    ]);
    expect(restorePreviousTurnState).toHaveBeenCalledTimes(1);
    expect(syncActiveSession).toHaveBeenCalledWith(null);
    expect(actions.setOptions).toHaveBeenCalledWith([]);
  });

  it('handles timeout errors by keeping current session and restoring previous turn state', () => {
    const feedback = { error: vi.fn() };
    const actions = { setOptions: vi.fn() };
    const restorePreviousTurnState = vi.fn();
    const syncActiveSession = vi.fn();
    const persistReadOnlySnapshot = vi.fn();
    const error = new ServiceError({
      code: 'REQUEST_TIMEOUT',
      message: 'Request timed out.',
    });

    handleStoryTurnSubmissionError({
      error,
      threadId: 'thread-4',
      messages: [{ role: 'assistant', content: 'Pending turn' }],
      feedback,
      actions,
      restorePreviousTurnState,
      syncActiveSession,
      persistReadOnlySnapshot,
    });

    expect(feedback.error).toHaveBeenCalledWith('Processing timed out. Please retry in a moment.');
    expect(restorePreviousTurnState).toHaveBeenCalledTimes(1);
    expect(syncActiveSession).not.toHaveBeenCalled();
    expect(persistReadOnlySnapshot).not.toHaveBeenCalled();
    expect(actions.setOptions).not.toHaveBeenCalled();
  });

  it('falls back to generic message when service code is not special-cased', () => {
    const feedback = { error: vi.fn() };
    const actions = { setOptions: vi.fn() };
    const restorePreviousTurnState = vi.fn();
    const syncActiveSession = vi.fn();
    const persistReadOnlySnapshot = vi.fn();

    handleStoryTurnSubmissionError({
      error: new Error('Network unstable'),
      threadId: 'thread-5',
      messages: [{ role: 'assistant', content: 'Pending turn' }],
      feedback,
      actions,
      restorePreviousTurnState,
      syncActiveSession,
      persistReadOnlySnapshot,
    });

    expect(feedback.error).toHaveBeenCalledWith('Network unstable');
    expect(restorePreviousTurnState).toHaveBeenCalledTimes(1);
    expect(syncActiveSession).not.toHaveBeenCalled();
    expect(persistReadOnlySnapshot).not.toHaveBeenCalled();
    expect(actions.setOptions).not.toHaveBeenCalled();
  });
});
