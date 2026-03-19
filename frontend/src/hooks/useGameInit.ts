import { useCallback, useEffect, useRef } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import { getCharacterImages, initializeStory } from '@/services/characterApi';
import { initGame } from '@/services/gameApi';
import type { GameMessage, GameSessionSnapshot, InitialGameData, StorySceneData } from '@/types/game';
import { resolveCharacterImageUrl } from '@/utils/game';
import {
  buildInitialAssistantMessages,
  hasStorySceneVisual,
  resolvePreferredCharacterId,
  resolveSelectedSceneTransition,
} from '@/utils/gameSession';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName, resolveStorySceneVisual } from '@/utils/storyScene';
import type { GameSessionInitActions } from './useGameState';

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
    getThreadSave,
    persistGameProgress,
    setActiveSession,
    setCurrentCharacterId,
  } = useGameFlow();

  const loadCharacterImageFromAPI = useCallback(
    (characterId: string | null) => {
      if (!characterId || ['undefined', 'null', ''].includes(String(characterId).trim())) {
        return;
      }

      getCharacterImages(String(characterId))
        .then((data) => {
          if (data.images?.length) {
            actions.setCharacterImageUrl(data.images[0]);
          }
        })
        .catch((error: unknown) => {
          const err = error as { message?: string };
          logger.warn('[game] failed to fetch character images:', err.message || error);
        });
    },
    [actions]
  );

  const setCharacterImage = useCallback(
    (characterId: string | null) => {
      const imageUrl = resolveCharacterImageUrl(flowState.characterDraft);
      if (imageUrl) {
        actions.setCharacterImageUrl(imageUrl);
        return;
      }

      loadCharacterImageFromAPI(characterId);
    },
    [actions, flowState.characterDraft, loadCharacterImageFromAPI]
  );

  const restoreSavedSnapshot = useCallback(
    (snapshot: GameSessionSnapshot | undefined, characterId?: string) => {
      if (!snapshot) {
        if (characterId) {
          setCharacterImage(characterId);
        }
        return;
      }

      actions.setDialogue(snapshot.currentDialogue);
      actions.setOptions(snapshot.currentOptions);

      if (snapshot.currentScene) {
        actions.enterScene(
          snapshot.currentScene,
          resolveSceneDisplayName(snapshot.currentScene) ?? snapshot.currentScene
        );
      }

      if (snapshot.shouldUseComposite && snapshot.compositeImageUrl) {
        actions.applyCompositeScene(snapshot.compositeImageUrl);
        return;
      }

      actions.applySceneVisual({
        sceneImageUrl: snapshot.sceneImageUrl ?? null,
        characterImageUrl: snapshot.characterImageUrl,
        clearCharacterImage: !snapshot.characterImageUrl,
      });

      if (snapshot.characterImageUrl) {
        return;
      }

      if (characterId) {
        setCharacterImage(characterId);
      } else {
        actions.setCharacterImageUrl(null);
      }
    },
    [actions, setCharacterImage]
  );

  const loadGameSave = useCallback(
    (threadId: string) => {
      try {
        const save = getThreadSave(threadId);
        if (save?.messages?.length) {
          actions.replaceMessages(save.messages);
          restoreSavedSnapshot(save.snapshot, save.characterId);
          feedback.success('Save loaded.');
          return true;
        }
      } catch (error: unknown) {
        logger.error('failed to load save:', error);
        feedback.error('Failed to load save.');
      }

      return false;
    },
    [actions, feedback, getThreadSave, restoreSavedSnapshot]
  );

  const saveGameProgress = useCallback(
    (
      threadId: string,
      messages: GameMessage[],
      characterId?: string,
      snapshot?: GameSessionSnapshot
    ) => {
      try {
        persistGameProgress({
          threadId,
          characterId,
          messages,
          snapshot,
        });
      } catch (error: unknown) {
        logger.error('failed to save progress:', error);
      }
    },
    [persistGameProgress]
  );

  const applyStoryData = useCallback(
    (storyData: InitialGameData | StorySceneData, characterId: string) => {
      if (storyData.sceneId) {
        actions.enterScene(
          storyData.sceneId,
          resolveSceneDisplayName(storyData.sceneId) ?? storyData.sceneId,
          'reset'
        );
      }

      const visual = resolveStorySceneVisual(storyData);
      if (visual.kind === 'composite') {
        actions.applyCompositeScene(visual.imageUrl);
      } else if (hasStorySceneVisual(storyData)) {
        actions.applySceneVisual({ sceneImageUrl: visual.imageUrl });
        setCharacterImage(characterId);
      } else {
        actions.applySceneVisual({ sceneImageUrl: null });
      }

      actions.setDialogue(storyData.characterDialogue);
      actions.setOptions(storyData.playerOptions);
    },
    [actions, setCharacterImage]
  );

  const initializeGame = useCallback(async () => {
    const characterDraft = flowState.characterDraft;
    const { restoreSession, activeSession, currentCharacterId } = flowState.runtimeSession;
    const fallbackCharacterId = resolvePreferredCharacterId({
      currentCharacterId,
      activeCharacterId: activeSession.characterId,
      draftCharacterId: characterDraft?.characterId,
    });
    const selectedSceneTransition = resolveSelectedSceneTransition(
      characterDraft?.selectedScene,
      resolveSceneDisplayName
    );

    if (restoreSession.threadId) {
      const restoreCharacterId = resolvePreferredCharacterId({
        currentCharacterId: restoreSession.characterId,
        activeCharacterId: fallbackCharacterId,
      });

      if (restoreCharacterId) {
        actions.setCharacterId(restoreCharacterId);
        setCurrentCharacterId(restoreCharacterId);
      }

      actions.setThreadId(restoreSession.threadId);
      setActiveSession({
        threadId: restoreSession.threadId,
        characterId: restoreCharacterId,
        initialGameData: null,
      });

      const restored = loadGameSave(restoreSession.threadId);
      clearRestoreSession();

      if (!restored) {
        logger.warn('[game] restore session found but no saved messages were loaded.');
      }
      return;
    }

    if (activeSession.threadId && activeSession.characterId) {
      actions.setThreadId(activeSession.threadId);
      actions.setCharacterId(activeSession.characterId);
      setCurrentCharacterId(activeSession.characterId);

      if (loadGameSave(activeSession.threadId)) {
        return;
      }

      if (activeSession.initialGameData) {
        try {
          const hasInitialVisual = hasStorySceneVisual(activeSession.initialGameData);

          if (hasInitialVisual) {
            applyStoryData(activeSession.initialGameData, activeSession.characterId);
          } else if (selectedSceneTransition) {
            actions.enterScene(
              selectedSceneTransition.sceneId,
              selectedSceneTransition.sceneName,
              'reset'
            );
          }

          const initialMessages = buildInitialAssistantMessages(activeSession.initialGameData);

          if (initialMessages.length > 0) {
            actions.replaceMessages(initialMessages);
          }

          if (!hasInitialVisual) {
            setCharacterImage(activeSession.characterId);
          }

          clearInitialGameData();
        } catch (error: unknown) {
          logger.error('failed to parse initial game data', error);
        }
      } else if (selectedSceneTransition) {
        try {
          actions.enterScene(
            selectedSceneTransition.sceneId,
            selectedSceneTransition.sceneName,
            'reset'
          );

          const imageUrl = resolveCharacterImageUrl(characterDraft);
          const storyData = await initializeStory(
            activeSession.threadId,
            activeSession.characterId,
            selectedSceneTransition.sceneId,
            imageUrl
          );

          applyStoryData(storyData, activeSession.characterId);
        } catch (error: unknown) {
          logger.error('failed to fetch initial story data', error);
        }
      }

      return;
    }

    if (!fallbackCharacterId) {
      return;
    }

    actions.setCharacterId(fallbackCharacterId);
    setCurrentCharacterId(fallbackCharacterId);

    try {
      const initRes = await initGame({ game_mode: 'solo', character_id: fallbackCharacterId });
      const newThreadId = initRes.thread_id;

      if (!newThreadId) {
        feedback.error('Missing thread id, cannot initialize game.');
        return;
      }

      actions.setThreadId(newThreadId);
      setActiveSession({
        threadId: newThreadId,
        characterId: fallbackCharacterId,
        initialGameData: null,
      });

      const imageUrl = resolveCharacterImageUrl(characterDraft);
      const storyData = await initializeStory(newThreadId, fallbackCharacterId, undefined, imageUrl);

      applyStoryData(storyData, fallbackCharacterId);
      actions.replaceMessages(buildInitialAssistantMessages(storyData));
    } catch (error: unknown) {
      logger.error('failed to initialize game', error);
      feedback.error('Failed to initialize game.');
    }
  }, [
    actions,
    applyStoryData,
    clearInitialGameData,
    clearRestoreSession,
    feedback,
    flowState.characterDraft,
    flowState.runtimeSession,
    loadGameSave,
    setActiveSession,
    setCharacterImage,
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
