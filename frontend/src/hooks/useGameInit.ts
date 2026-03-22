import { useCallback, useEffect, useRef } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { initGame, initializeStory } from '@/services/gameApi';
import { readStoryThreadSave } from '@/storage/storySessionCache';
import type { GameMessage, GameSessionSnapshot } from '@/types/game';
import { resolveCharacterImageUrl } from '@/utils/game';
import { buildInitialAssistantMessages, resolveGameInitializationPlan } from '@/utils/gameSession';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName } from '@/utils/storyScene';
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

  const hydrateSessionIdentity = useCallback(
    (threadId: string, characterId: string | null) => {
      actions.setThreadId(threadId);
      actions.setCharacterId(characterId);

      if (characterId) {
        setCurrentCharacterId(characterId);
      }
    },
    [actions, setCurrentCharacterId]
  );

  const enterReadonlySnapshotMode = useCallback(
    (characterId: string | null) => {
      clearActiveSession();
      actions.setThreadId(null);
      actions.setCharacterId(characterId);

      if (characterId) {
        setCurrentCharacterId(characterId);
      }
    },
    [actions, clearActiveSession, setCurrentCharacterId]
  );

  const clearInvalidSessionState = useCallback(
    (characterId: string | null) => {
      clearActiveSession();
      actions.setThreadId(null);
      actions.setCharacterId(characterId);
    },
    [actions, clearActiveSession]
  );

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
      switch (initializationPlan.kind) {
        case 'restore-session': {
          const restoreResult = await restoreFromServerSnapshot(
            initializationPlan.threadId,
            initializationPlan.characterId
          );
          clearRestoreSession();

          if (restoreResult.source === 'server' && restoreResult.restored) {
            hydrateSessionIdentity(initializationPlan.threadId, initializationPlan.characterId);
            setActiveSession({
              threadId: initializationPlan.threadId,
              characterId: initializationPlan.characterId,
              initialGameData: null,
            });
            return;
          }

          if (restoreResult.source === 'local' && restoreResult.error) {
            enterReadonlySnapshotMode(initializationPlan.characterId);
            notifyLocalRestoreFallback(restoreResult.error);
            return;
          }

          if (!restoreResult.restored) {
            clearInvalidSessionState(initializationPlan.characterId);
            notifyRestoreFailure(restoreResult.error, 'Failed to restore story session.');
          }
          return;
        }
        case 'resume-session': {
          const hasLocalSave = Boolean(readStoryThreadSave(initializationPlan.threadId));
          if (initializationPlan.initialGameData && !hasLocalSave) {
            hydrateSessionIdentity(initializationPlan.threadId, initializationPlan.characterId);
            applyInitialEntryData(initializationPlan.initialGameData, {
              characterId: initializationPlan.characterId,
              selectedSceneTransition: initializationPlan.selectedSceneTransition,
            });
            clearInitialGameData();
            return;
          }

          const restoreResult = await restoreFromServerSnapshot(
            initializationPlan.threadId,
            initializationPlan.characterId
          );
          clearInitialGameData();

          if (restoreResult.source === 'server' && restoreResult.restored) {
            hydrateSessionIdentity(initializationPlan.threadId, initializationPlan.characterId);
            return;
          }

          if (restoreResult.source === 'local' && restoreResult.error) {
            enterReadonlySnapshotMode(initializationPlan.characterId);
            notifyLocalRestoreFallback(restoreResult.error);
            return;
          }

          clearInvalidSessionState(initializationPlan.characterId);
          notifyRestoreFailure(restoreResult.error, 'Failed to resume the story session.');
          return;
        }
        case 'fresh-session': {
          actions.setCharacterId(initializationPlan.characterId);
          setCurrentCharacterId(initializationPlan.characterId);

          const initTelemetryMetadata = {
            initializationKind: initializationPlan.kind,
            characterId: initializationPlan.characterId,
            sceneId: initializationPlan.selectedSceneTransition?.sceneId ?? null,
          };

          try {
            trackFrontendTelemetry({
              domain: 'story',
              event: 'story.init',
              status: 'requested',
              metadata: initTelemetryMetadata,
            });
            const initRes = await initGame({
              gameMode: 'solo',
              characterId: initializationPlan.characterId,
            });
            const newThreadId = initRes.threadId;

            hydrateSessionIdentity(newThreadId, initializationPlan.characterId);
            setActiveSession({
              threadId: newThreadId,
              characterId: initializationPlan.characterId,
              initialGameData: null,
            });

            const imageUrl = resolveCharacterImageUrl(characterDraft);
            const storyData = await initializeStory(
              newThreadId,
              initializationPlan.characterId,
              initializationPlan.selectedSceneTransition?.sceneId,
              imageUrl
            );

            applyStoryData(storyData, {
              characterId: initializationPlan.characterId,
              sceneMode: initializationPlan.selectedSceneTransition ? 'reset' : 'silent',
            });
            actions.replaceMessages(buildInitialAssistantMessages(storyData));
            trackFrontendTelemetry({
              domain: 'story',
              event: 'story.init',
              status: 'succeeded',
              metadata: {
                ...initTelemetryMetadata,
                threadId: newThreadId,
                initialSceneId: storyData.sceneId ?? null,
              },
            });
          } catch (error: unknown) {
            trackFrontendTelemetry({
              domain: 'story',
              event: 'story.init',
              status: 'failed',
              metadata: initTelemetryMetadata,
              cause: error,
            });
            logger.error('failed to initialize game', error);
            feedback.error('Failed to initialize game.');
          }
          return;
        }
        case 'idle':
        default:
          return;
      }
    } finally {
      actions.stopLoading();
    }
  }, [
    actions,
    applyInitialEntryData,
    applyStoryData,
    clearInitialGameData,
    clearRestoreSession,
    clearInvalidSessionState,
    clearActiveSession,
    enterReadonlySnapshotMode,
    feedback,
    flowState.characterDraft,
    flowState.runtimeSession,
    hydrateSessionIdentity,
    notifyLocalRestoreFallback,
    notifyRestoreFailure,
    restoreFromServerSnapshot,
    setActiveSession,
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
