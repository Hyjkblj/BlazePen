import { useCallback } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { initGame, initializeStory, processGameInput } from '@/services/gameApi';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import type { GameTurnResult, PlayerOption } from '@/types/game';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName, resolveStorySceneVisual } from '@/utils/storyScene';
import type { GameSessionActions } from './useGameState';

interface StoryTurnSubmissionState {
  loading: boolean;
  threadId: string | null;
  currentOptions: PlayerOption[];
  currentDialogue: string;
  currentScene: string | null;
  characterImageUrl: string | null;
}

interface UseStoryTurnSubmissionParams {
  feedback: FeedbackContextValue;
  state: StoryTurnSubmissionState;
  actions: Pick<
    GameSessionActions,
    | 'prepareOptionSelection'
    | 'setThreadId'
    | 'setDialogue'
    | 'setOptions'
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
}: UseStoryTurnSubmissionParams): UseStoryTurnSubmissionResult {
  const {
    loading,
    threadId,
    currentOptions,
    currentDialogue,
    currentScene,
    characterImageUrl,
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

      if (responseData.isGameFinished) {
        feedback.info('Story finished.');
      }
    },
    [actions, applyResponseVisual, feedback]
  );

  const recoverExpiredSession = useCallback(async (): Promise<boolean> => {
    if (!preferredCharacterId) {
      feedback.error('Story session expired. Please restart the story.');
      return false;
    }

    try {
      const initResponse = await initGame({
        gameMode: 'solo',
        characterId: preferredCharacterId,
      });

      const openingState = await initializeStory(
        initResponse.threadId,
        preferredCharacterId,
        currentScene ?? undefined,
        characterImageUrl ?? undefined
      );

      syncActiveSession(initResponse.threadId);
      actions.rollbackPendingUserMessage();
      applyResponseVisual({
        threadId: initResponse.threadId,
        sessionRestored: true,
        needReselectOption: false,
        restoredFromThreadId: threadId,
        ...openingState,
      });
      actions.setDialogue(openingState.characterDialogue);
      actions.setOptions(openingState.playerOptions);
      feedback.success('Game session restored with a fresh story state.');
      return true;
    } catch (error: unknown) {
      logger.error('[game] failed to recover session', error);
      feedback.error('Game session could not be recovered. Please restart the story.');
      return false;
    }
  }, [
    actions,
    applyResponseVisual,
    characterImageUrl,
    currentScene,
    feedback,
    preferredCharacterId,
    syncActiveSession,
    threadId,
  ]);

  const restorePreviousTurnState = useCallback(() => {
    actions.setDialogue(currentDialogue);
    actions.setOptions(currentOptions);
    actions.rollbackPendingUserMessage();
  }, [actions, currentDialogue, currentOptions]);

  const applyReselectResponse = useCallback(
    (responseData: GameTurnResult) => {
      actions.rollbackPendingUserMessage();
      applyResponseVisual(responseData);
      actions.setDialogue(responseData.characterDialogue);
      actions.setOptions(responseData.playerOptions);
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

      actions.prepareOptionSelection(selectedOption.text);

      try {
        const response = await processGameInput({
          threadId,
          userInput: `option:${optionIndex + 1}`,
          characterId: preferredCharacterId || undefined,
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
        logger.error('Failed to process game option:', error);

        if (isServiceError(error) && error.code === 'SESSION_EXPIRED') {
          feedback.warning('Game session expired. Trying to recover...');
          const recovered = await recoverExpiredSession();
          if (!recovered) {
            restorePreviousTurnState();
            syncActiveSession(null);
            actions.setOptions([]);
          }
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
      currentOptions,
      feedback,
      loading,
      preferredCharacterId,
      recoverExpiredSession,
      restorePreviousTurnState,
      syncActiveSession,
      threadId,
    ]
  );

  return {
    selectOption,
  };
}
