import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import type { GameMessage, GameTurnResult } from '@/types/game';
import { resolveSceneDisplayName, resolveStorySceneVisual } from '@/utils/storyScene';
import type { GameSessionActions } from './useGameState';

export interface StoryTurnResponseExecutorOptions {
  response: GameTurnResult;
  currentScene: string | null;
  ensureCharacterImage: () => void;
  feedback: Pick<FeedbackContextValue, 'info'>;
  actions: Pick<
    GameSessionActions,
    | 'setDialogue'
    | 'setOptions'
    | 'setGameFinished'
    | 'enterScene'
    | 'applyCompositeScene'
    | 'applySceneVisual'
    | 'appendMessage'
  >;
}

export interface StoryTurnReselectExecutorOptions {
  response: GameTurnResult;
  currentScene: string | null;
  ensureCharacterImage: () => void;
  actions: Pick<
    GameSessionActions,
    | 'rollbackPendingUserMessage'
    | 'setDialogue'
    | 'setOptions'
    | 'setGameFinished'
    | 'enterScene'
    | 'applyCompositeScene'
    | 'applySceneVisual'
  >;
}

export interface StoryTurnErrorExecutorOptions {
  error: unknown;
  threadId: string;
  messages: GameMessage[];
  feedback: Pick<FeedbackContextValue, 'error'>;
  actions: Pick<GameSessionActions, 'setOptions'>;
  restorePreviousTurnState: () => void;
  syncActiveSession: (nextThreadId: string | null) => void;
  persistReadOnlySnapshot: (threadId: string, messages: GameMessage[]) => void;
}

const applyResponseVisual = ({
  response,
  currentScene,
  ensureCharacterImage,
  actions,
}: {
  response: GameTurnResult;
  currentScene: string | null;
  ensureCharacterImage: () => void;
  actions: Pick<
    GameSessionActions,
    'enterScene' | 'applyCompositeScene' | 'applySceneVisual'
  >;
}) => {
  if (response.sceneId && response.sceneId !== currentScene) {
    actions.enterScene(
      response.sceneId,
      resolveSceneDisplayName(response.sceneId) ?? response.sceneId,
      'advance'
    );
  }

  const visual = resolveStorySceneVisual(response);
  if (visual.kind === 'composite') {
    actions.applyCompositeScene(visual.imageUrl);
    return;
  }

  if (response.sceneId || response.sceneImageUrl) {
    actions.applySceneVisual({ sceneImageUrl: visual.imageUrl });
    ensureCharacterImage();
  }
};

export const applyStoryTurnResponseState = ({
  response,
  currentScene,
  ensureCharacterImage,
  feedback,
  actions,
}: StoryTurnResponseExecutorOptions) => {
  applyResponseVisual({
    response,
    currentScene,
    ensureCharacterImage,
    actions,
  });

  if (response.characterDialogue) {
    actions.setDialogue(response.characterDialogue);
    actions.appendMessage({
      role: 'assistant',
      content: response.characterDialogue,
    });
  }

  actions.setOptions(response.playerOptions);
  actions.setGameFinished(response.isGameFinished);

  if (response.isGameFinished) {
    feedback.info('Story finished.');
  }
};

export const applyStoryTurnReselectState = ({
  response,
  currentScene,
  ensureCharacterImage,
  actions,
}: StoryTurnReselectExecutorOptions) => {
  actions.rollbackPendingUserMessage();
  applyResponseVisual({
    response,
    currentScene,
    ensureCharacterImage,
    actions,
  });
  actions.setDialogue(response.characterDialogue);
  actions.setOptions(response.playerOptions);
  actions.setGameFinished(response.isGameFinished);
};

const isSessionUnrecoverableError = (error: unknown) =>
  isServiceError(error) &&
  (error.code === 'STORY_SESSION_EXPIRED' ||
    error.code === 'STORY_SESSION_NOT_FOUND' ||
    error.code === 'SESSION_EXPIRED');

export const handleStoryTurnSubmissionError = ({
  error,
  threadId,
  messages,
  feedback,
  actions,
  restorePreviousTurnState,
  syncActiveSession,
  persistReadOnlySnapshot,
}: StoryTurnErrorExecutorOptions) => {
  if (isServiceError(error) && error.code === 'STORY_SESSION_RESTORE_FAILED') {
    feedback.error('Game session could not be recovered. Please restart the story.');
    persistReadOnlySnapshot(threadId, messages);
    restorePreviousTurnState();
    syncActiveSession(null);
    actions.setOptions([]);
    return;
  }

  if (isSessionUnrecoverableError(error)) {
    feedback.error('Story session expired. Please restart the story.');
    persistReadOnlySnapshot(threadId, messages);
    restorePreviousTurnState();
    syncActiveSession(null);
    actions.setOptions([]);
    return;
  }

  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    feedback.error('Processing timed out. Please retry in a moment.');
    restorePreviousTurnState();
    return;
  }

  feedback.error(getServiceErrorMessage(error, 'Failed to process the selected option.'));
  restorePreviousTurnState();
};
