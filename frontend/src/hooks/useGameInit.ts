import { useCallback, useEffect, useRef } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import type { GameMessage, GameSessionSnapshot } from '@/types/game';
import { resolveGameInitializationPlan } from '@/utils/gameSession';
import { resolveSceneDisplayName } from '@/utils/storyScene';
import { executeGameInitializationPlan } from './gameInitializationExecutor';
import type { GameSessionInitActions } from './useGameState';
import { useStorySessionRestore } from './useStorySessionRestore';

export interface UseGameInitResult {
  loadGameSave: (threadId: string) => boolean;
  saveGameProgress: (
    threadId: string,
    messages: GameMessage[],
    characterId?: string,
    snapshot?: GameSessionSnapshot
  ) => void;
  setCharacterImage: (characterId: string | null) => void;
}

export function useGameInit(actions: GameSessionInitActions): UseGameInitResult {
  const feedback = useFeedback();
  const {
    state: flowState,
    clearInitialGameData,
    clearRestoreSession,
    clearActiveSession,
    setActiveSession,
    setCurrentCharacterId,
  } = useGameFlow();

  const {
    loadGameSave,
    saveGameProgress,
    setCharacterImage,
    applyStoryData,
    applyInitialEntryData,
    restoreFromServerSnapshot,
    notifyLocalRestoreFallback,
    notifyRestoreFailure,
  } = useStorySessionRestore({
    actions,
    feedback,
    characterDraft: flowState.characterDraft,
  });

  const initializeGame = useCallback(async () => {
    const characterDraft = flowState.characterDraft;
    const { restoreSession, activeSession, currentCharacterId } = flowState.runtimeSession;
    const initializationPlan = resolveGameInitializationPlan({
      restoreThreadId: restoreSession.threadId,
      restoreCharacterId: restoreSession.characterId,
      activeThreadId: activeSession.threadId,
      activeCharacterId: activeSession.characterId,
      currentCharacterId,
      draftCharacterId: characterDraft?.characterId,
      initialGameData: activeSession.initialGameData,
      selectedScene: characterDraft?.selectedScene,
      resolveSceneName: resolveSceneDisplayName,
    });

    actions.startLoading();

    try {
      await executeGameInitializationPlan({
        plan: initializationPlan,
        actions,
        feedback,
        characterDraft,
        clearRestoreSession,
        clearInitialGameData,
        clearActiveSession,
        setActiveSession,
        setCurrentCharacterId,
        applyStoryData,
        applyInitialEntryData,
        restoreFromServerSnapshot,
        notifyLocalRestoreFallback,
        notifyRestoreFailure,
      });
    } finally {
      actions.stopLoading();
    }
  }, [
    actions,
    applyInitialEntryData,
    applyStoryData,
    clearInitialGameData,
    clearRestoreSession,
    clearActiveSession,
    feedback,
    flowState.characterDraft,
    flowState.runtimeSession,
    notifyLocalRestoreFallback,
    notifyRestoreFailure,
    restoreFromServerSnapshot,
    setActiveSession,
    setCurrentCharacterId,
  ]);

  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) {
      return;
    }

    initializedRef.current = true;
    void initializeGame();
  }, [initializeGame]);

  return { loadGameSave, saveGameProgress, setCharacterImage };
}
