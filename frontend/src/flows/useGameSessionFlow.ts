import { useCallback, useEffect } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import {
  useGameAssetFeedback,
  useGameInit,
  useGameState,
  useGameTts,
  useStoryEnding,
  useStorySessionTranscript,
  useStoryTurnSubmission,
} from '@/hooks';
import type { StoryEndingStatus, StoryTranscriptEntry } from '@/hooks';
import type { PlayerOption, StoryEndingSummary } from '@/types/game';
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
  optionsDisabledReason: string | null;
  hasTranscript: boolean;
  transcriptEntries: StoryTranscriptEntry[];
  isTranscriptDialogOpen: boolean;
  isGameFinished: boolean;
  canViewEnding: boolean;
  isEndingDialogOpen: boolean;
  endingStatus: StoryEndingStatus;
  endingSummary: StoryEndingSummary | null;
  endingError: string | null;
  dismissTransition: () => void;
  handleCharacterAssetError: () => void;
  handleCompositeAssetError: () => void;
  handleSceneAssetError: () => void;
  openTranscriptDialog: () => void;
  closeTranscriptDialog: () => void;
  openEndingDialog: () => void;
  closeEndingDialog: () => void;
  retryEndingSummary: () => void;
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
    isGameFinished,
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
  const optionsDisabledReason =
    !threadId && messages.length > 0
      ? '当前为本地只读快照，无法继续提交。请稍后重试恢复或重新开始故事。'
      : null;

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
      isGameFinished,
    },
    actions,
    preferredCharacterId,
    setCharacterImage,
    syncActiveSession,
  });

  const {
    hasTranscript,
    transcriptEntries,
    isTranscriptDialogOpen,
    openTranscriptDialog,
    closeTranscriptDialog,
  } = useStorySessionTranscript({
    messages,
  });

  const {
    isEndingDialogOpen,
    endingSummary,
    endingStatus,
    endingError,
    canViewEnding,
    openEndingDialog,
    closeEndingDialog,
    retryEndingSummary,
  } = useStoryEnding({
    threadId,
    isGameFinished,
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
    optionsDisabledReason,
    hasTranscript,
    transcriptEntries,
    isTranscriptDialogOpen,
    isGameFinished,
    canViewEnding,
    isEndingDialogOpen,
    endingStatus,
    endingSummary,
    endingError,
    dismissTransition,
    handleCharacterAssetError,
    handleCompositeAssetError,
    handleSceneAssetError,
    openTranscriptDialog,
    closeTranscriptDialog,
    openEndingDialog,
    closeEndingDialog,
    retryEndingSummary,
    selectOption,
  };
}
