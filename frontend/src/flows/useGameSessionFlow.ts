import { useCallback, useEffect } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import {
  useGameAssetFeedback,
  useGameInit,
  useGameState,
  useGameTts,
  useStoryTurnSubmission,
} from '@/hooks';
import type { PlayerOption } from '@/types/game';
import { resolvePreferredCharacterId } from '@/utils/gameSession';
import { logger } from '@/utils/logger';

export interface UseGameSessionFlowResult {
  actNumber: number;
  showTransition: boolean;
  transitionSceneName: string;
  loading: boolean;
  shouldUseComposite: boolean;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  currentDialogue: string;
  currentOptions: PlayerOption[];
  dismissTransition: () => void;
  handleCharacterAssetError: () => void;
  handleCompositeAssetError: () => void;
  handleSceneAssetError: () => void;
  selectOption: (optionIndex: number) => Promise<void>;
}

export function useGameSessionFlow(): UseGameSessionFlowResult {
  const feedback = useFeedback();
  const { state: flowState, setActiveSession, clearActiveSession } = useGameFlow();
  const gameState = useGameState();
  const { actions, derived } = gameState;
  const { saveGameProgress, setCharacterImage } = useGameInit(actions);

  const {
    actNumber,
    showTransition,
    transitionSceneName,
    loading,
    shouldUseComposite,
    compositeImageUrl,
    sceneImageUrl,
    characterImageUrl,
    currentDialogue,
    currentOptions,
    currentScene,
    characterId,
    messages,
    threadId,
  } = gameState.state;

  useGameTts(currentDialogue, characterId);

  useEffect(() => {
    if (flowState.characterDraft?.voiceConfig) {
      logger.debug('[game] character voice config:', flowState.characterDraft.voiceConfig);
    }
  }, [flowState.characterDraft?.voiceConfig]);

  useEffect(() => {
    actions.scrollToBottom();
    if (!threadId || messages.length === 0) {
      return;
    }

    saveGameProgress(threadId, messages, characterId ?? undefined, derived.persistenceSnapshot);
  }, [
    actions,
    characterId,
    derived.persistenceSnapshot,
    messages,
    saveGameProgress,
    threadId,
  ]);

  const preferredCharacterId = resolvePreferredCharacterId({
    currentCharacterId: characterId,
    activeCharacterId: flowState.runtimeSession.currentCharacterId,
    draftCharacterId: flowState.characterDraft?.characterId,
  });

  const syncActiveSession = useCallback(
    (nextThreadId: string | null) => {
      if (!nextThreadId) {
        clearActiveSession();
        actions.setThreadId(null);
        return;
      }

      actions.setThreadId(nextThreadId);

      if (!preferredCharacterId) {
        return;
      }

      setActiveSession({
        threadId: nextThreadId,
        characterId: preferredCharacterId,
        initialGameData: null,
      });
    },
    [actions, clearActiveSession, preferredCharacterId, setActiveSession]
  );

  const { selectOption } = useStoryTurnSubmission({
    feedback,
    state: {
      loading,
      threadId,
      currentOptions,
      currentDialogue,
      currentScene,
      characterImageUrl,
    },
    actions,
    preferredCharacterId,
    setCharacterImage,
    syncActiveSession,
  });

  const dismissTransition = () => {
    actions.clearSceneTransition();
  };

  const {
    handleCompositeAssetError,
    handleSceneAssetError,
    handleCharacterAssetError,
  } = useGameAssetFeedback({
    feedback,
    actions,
    compositeImageUrl,
    sceneImageUrl,
    characterImageUrl,
  });

  return {
    actNumber,
    showTransition,
    transitionSceneName,
    loading,
    shouldUseComposite,
    compositeImageUrl,
    sceneImageUrl,
    characterImageUrl,
    currentDialogue,
    currentOptions,
    dismissTransition,
    handleCharacterAssetError,
    handleCompositeAssetError,
    handleSceneAssetError,
    selectOption,
  };
}
