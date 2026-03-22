import { useCallback } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { submitStoryTurn } from '@/services/storyTurnService';
import type { GameMessage, PlayerOption } from '@/types/game';
import { logger } from '@/utils/logger';
import {
  applyStoryTurnReselectState,
  applyStoryTurnResponseState,
  handleStoryTurnSubmissionError,
} from './storyTurnSubmissionExecutor';
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

  const restorePreviousTurnState = useCallback(() => {
    actions.setDialogue(currentDialogue);
    actions.setOptions(currentOptions);
    actions.setGameFinished(isGameFinished);
    actions.rollbackPendingUserMessage();
  }, [actions, currentDialogue, currentOptions, isGameFinished]);

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
          applyStoryTurnReselectState({
            response,
            currentScene,
            ensureCharacterImage,
            actions,
          });
          return;
        }

        if (response.sessionRestored) {
          feedback.info('Game session restored.');
        }

        applyStoryTurnResponseState({
          response,
          currentScene,
          ensureCharacterImage,
          feedback,
          actions,
        });
      } catch (error: unknown) {
        trackFrontendTelemetry({
          domain: 'story',
          event: 'story.turn.submit',
          status: 'failed',
          metadata: submitTelemetryMetadata,
          cause: error,
        });
        logger.error('Failed to process game option:', error);

        handleStoryTurnSubmissionError({
          error,
          threadId,
          messages,
          feedback,
          actions,
          restorePreviousTurnState,
          syncActiveSession,
          persistReadOnlySnapshot,
        });
      } finally {
        actions.stopLoading();
      }
    },
    [
      actions,
      currentScene,
      currentOptions,
      ensureCharacterImage,
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
