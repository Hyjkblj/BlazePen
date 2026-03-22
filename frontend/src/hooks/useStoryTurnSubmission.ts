import { useCallback } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { submitStoryTurn } from '@/services/storyTurnService';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import type { GameMessage, GameTurnResult, PlayerOption } from '@/types/game';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName, resolveStorySceneVisual } from '@/utils/storyScene';
import type { GameSessionActions } from './useGameState';

interface StoryTurnSubmissionState {
  messages: GameMessage[];
  loading: boolean;
  threadId: string | null;
  currentOptions: PlayerOption[];
  currentDialogue: string;
  currentScene: string | null;
  characterImageUrl: string | null;
  isGameFinished: boolean;
}

interface UseStoryTurnSubmissionParams {
  feedback: FeedbackContextValue;
  state: StoryTurnSubmissionState;
  actions: Pick<
    GameSessionActions,
    | 'prepareOptionSelection'
    | 'setDialogue'
    | 'setOptions'
    | 'setGameFinished'
    | 'rollbackPendingUserMessage'
    | 'stopLoading'
    | 'enterScene'
    | 'applyCompositeScene'
    | 'applySceneVisual'
    | 'appendMessage'
  >;
  preferredCharacterId: string | null;
  setCharacterImage: (characterId: string | null) => void;
  syncActiveSession: (nextThreadId: string | null) => void;
  persistReadOnlySnapshot: (threadId: string, messages: GameMessage[]) => void;
}

export interface UseStoryTurnSubmissionResult {
  selectOption: (optionIndex: number) => Promise<void>;
}

export function useStoryTurnSubmission({
  feedback,
  state,
  actions,
  preferredCharacterId,
  setCharacterImage,
  syncActiveSession,
  persistReadOnlySnapshot,
}: UseStoryTurnSubmissionParams): UseStoryTurnSubmissionResult {
  const {
    messages,
    loading,
    threadId,
    currentOptions,
    currentDialogue,
    currentScene,
    characterImageUrl,
    isGameFinished,
  } = state;

  const ensureCharacterImage = useCallback(() => {
    if (characterImageUrl) {
      return;
    }

    setCharacterImage(preferredCharacterId);
  }, [characterImageUrl, preferredCharacterId, setCharacterImage]);

  const applyResponseVisual = useCallback(
    (responseData: GameTurnResult) => {
      if (responseData.sceneId && responseData.sceneId !== currentScene) {
        actions.enterScene(
          responseData.sceneId,
          resolveSceneDisplayName(responseData.sceneId) ?? responseData.sceneId,
          'advance'
        );
      }

      const visual = resolveStorySceneVisual(responseData);
      if (visual.kind === 'composite') {
        actions.applyCompositeScene(visual.imageUrl);
      } else if (responseData.sceneId || responseData.sceneImageUrl) {
        actions.applySceneVisual({ sceneImageUrl: visual.imageUrl });
        ensureCharacterImage();
      }
    },
    [actions, currentScene, ensureCharacterImage]
  );

  const applyGameResponse = useCallback(
    (responseData: GameTurnResult) => {
      applyResponseVisual(responseData);

      if (responseData.characterDialogue) {
        actions.setDialogue(responseData.characterDialogue);
        actions.appendMessage({
          role: 'assistant',
          content: responseData.characterDialogue,
        });
      }

      actions.setOptions(responseData.playerOptions);
      actions.setGameFinished(responseData.isGameFinished);

      if (responseData.isGameFinished) {
        feedback.info('Story finished.');
      }
    },
    [actions, applyResponseVisual, feedback]
  );

  const restorePreviousTurnState = useCallback(() => {
    actions.setDialogue(currentDialogue);
    actions.setOptions(currentOptions);
    actions.setGameFinished(isGameFinished);
    actions.rollbackPendingUserMessage();
  }, [actions, currentDialogue, currentOptions, isGameFinished]);

  const applyReselectResponse = useCallback(
    (responseData: GameTurnResult) => {
      actions.rollbackPendingUserMessage();
      applyResponseVisual(responseData);
      actions.setDialogue(responseData.characterDialogue);
      actions.setOptions(responseData.playerOptions);
      actions.setGameFinished(responseData.isGameFinished);
    },
    [actions, applyResponseVisual]
  );

  const selectOption = useCallback(
    async (optionIndex: number) => {
      if (loading || !threadId) {
        return;
      }

      const selectedOption = currentOptions[optionIndex];
      if (!selectedOption) {
        return;
      }

      const submitTelemetryMetadata = {
        threadId,
        optionIndex: optionIndex + 1,
        optionId: selectedOption.id,
        sceneId: currentScene,
      };

      actions.prepareOptionSelection(selectedOption.text);

      try {
        trackFrontendTelemetry({
          domain: 'story',
          event: 'story.turn.submit',
          status: 'requested',
          metadata: submitTelemetryMetadata,
        });
        const response = await submitStoryTurn({
          threadId,
          userInput: `option:${optionIndex + 1}`,
          characterId: preferredCharacterId,
        });

        trackFrontendTelemetry({
          domain: 'story',
          event: 'story.turn.submit',
          status: 'succeeded',
          metadata: {
            ...submitTelemetryMetadata,
            nextThreadId: response.threadId ?? threadId,
            sessionRestored: response.sessionRestored === true,
            needReselectOption: response.needReselectOption === true,
            isGameFinished: response.isGameFinished === true,
          },
        });

        if (response.threadId && response.threadId !== threadId) {
          syncActiveSession(response.threadId);
        }

        if (response.needReselectOption) {
          feedback.warning('Game session restored. Please choose an option again.');
          applyReselectResponse(response);
          return;
        }

        if (response.sessionRestored) {
          feedback.info('Game session restored.');
        }

        applyGameResponse(response);
      } catch (error: unknown) {
        trackFrontendTelemetry({
          domain: 'story',
          event: 'story.turn.submit',
          status: 'failed',
          metadata: submitTelemetryMetadata,
          cause: error,
        });
        logger.error('Failed to process game option:', error);

        if (isServiceError(error) && error.code === 'STORY_SESSION_RESTORE_FAILED') {
          feedback.error('Game session could not be recovered. Please restart the story.');
          persistReadOnlySnapshot(threadId, messages);
          restorePreviousTurnState();
          syncActiveSession(null);
          actions.setOptions([]);
        } else if (
          isServiceError(error) &&
          (error.code === 'STORY_SESSION_EXPIRED' ||
            error.code === 'STORY_SESSION_NOT_FOUND' ||
            error.code === 'SESSION_EXPIRED')
        ) {
          feedback.error('Story session expired. Please restart the story.');
          persistReadOnlySnapshot(threadId, messages);
          restorePreviousTurnState();
          syncActiveSession(null);
          actions.setOptions([]);
        } else if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
          feedback.error('Processing timed out. Please retry in a moment.');
          restorePreviousTurnState();
        } else {
          feedback.error(getServiceErrorMessage(error, 'Failed to process the selected option.'));
          restorePreviousTurnState();
        }
      } finally {
        actions.stopLoading();
      }
    },
    [
      actions,
      applyGameResponse,
      applyReselectResponse,
      currentScene,
      currentOptions,
      feedback,
      loading,
      messages,
      persistReadOnlySnapshot,
      preferredCharacterId,
      restorePreviousTurnState,
      syncActiveSession,
      threadId,
    ]
  );

  return {
    selectOption,
  };
}
