import { useCallback, useEffect, useRef } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import { getSceneNameById } from '@/config/scenes';
import { getCharacterImages, initializeStory } from '@/services/characterApi';
import { initGame } from '@/services/gameApi';
import * as gameStorage from '@/storage/gameStorage';
import type { GameMessage, GameSessionSnapshot, PlayerOption } from '@/types/game';
import { getFallbackSceneImageUrls, resolveCharacterImageUrl } from '@/utils/game';
import { logger } from '@/utils/logger';
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

interface StoryData {
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
}

export function useGameInit(actions: GameSessionInitActions): UseGameInitResult {
  const feedback = useFeedback();
  const {
    state: flowState,
    clearInitialGameData,
    clearRestoreSession,
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
        actions.enterScene(snapshot.currentScene, getSceneNameById(snapshot.currentScene));
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
        const save = gameStorage.getGameSave(threadId);
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
    [actions, feedback, restoreSavedSnapshot]
  );

  const saveGameProgress = useCallback(
    (
      threadId: string,
      messages: GameMessage[],
      characterId?: string,
      snapshot?: GameSessionSnapshot
    ) => {
      try {
        const lastMessage = messages.length > 0 ? messages[messages.length - 1].content : undefined;

        gameStorage.setGameSave({
          threadId,
          characterId,
          messages,
          lastMessage,
          snapshot,
          timestamp: Date.now(),
        });

        gameStorage.setMainGameSave({
          threadId,
          characterId,
          lastMessage,
          snapshot,
          timestamp: Date.now(),
        });
      } catch (error: unknown) {
        logger.error('failed to save progress:', error);
      }
    },
    []
  );

  const applyStoryData = useCallback(
    (storyData: StoryData, characterId: string) => {
      if (storyData.scene) {
        actions.enterScene(storyData.scene, getSceneNameById(storyData.scene), 'reset');
      }

      if (storyData.composite_image_url) {
        actions.applyCompositeScene(storyData.composite_image_url);
      } else if (storyData.scene_image_url) {
        actions.applySceneVisual({ sceneImageUrl: storyData.scene_image_url });
        setCharacterImage(characterId);
      } else if (storyData.scene) {
        actions.applySceneVisual({ sceneImageUrl: getFallbackSceneImageUrls(storyData.scene)[0] });
        setCharacterImage(characterId);
      } else {
        actions.applySceneVisual({ sceneImageUrl: null });
      }

      actions.setDialogue(storyData.character_dialogue);
      actions.setOptions(storyData.player_options);
    },
    [actions, setCharacterImage]
  );

  const initializeGame = useCallback(async () => {
    const characterDraft = flowState.characterDraft;
    const { restoreSession, activeSession, currentCharacterId } = flowState.runtimeSession;
    const fallbackCharacterId =
      currentCharacterId || activeSession.characterId || characterDraft?.characterId || null;

    if (restoreSession.threadId) {
      const restoreCharacterId = restoreSession.characterId || fallbackCharacterId || null;

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
          if (
            activeSession.initialGameData.composite_image_url ||
            activeSession.initialGameData.scene_image_url ||
            activeSession.initialGameData.scene
          ) {
            applyStoryData(activeSession.initialGameData, activeSession.characterId);
          } else if (characterDraft?.selectedScene?.id) {
            actions.enterScene(
              characterDraft.selectedScene.id,
              characterDraft.selectedScene.name ?? getSceneNameById(characterDraft.selectedScene.id),
              'reset'
            );
          }

          const initialMessages: GameMessage[] = [];
          if (activeSession.initialGameData.character_dialogue) {
            initialMessages.push({
              role: 'assistant',
              content: activeSession.initialGameData.character_dialogue,
            });
          }

          if (initialMessages.length > 0) {
            actions.replaceMessages(initialMessages);
          }

          if (
            !activeSession.initialGameData.composite_image_url &&
            !activeSession.initialGameData.scene_image_url &&
            !activeSession.initialGameData.scene
          ) {
            setCharacterImage(activeSession.characterId);
          }

          clearInitialGameData();
        } catch (error: unknown) {
          logger.error('failed to parse initial game data', error);
        }
      } else if (characterDraft?.selectedScene?.id) {
        try {
          actions.enterScene(
            characterDraft.selectedScene.id,
            characterDraft.selectedScene.name ?? getSceneNameById(characterDraft.selectedScene.id),
            'reset'
          );

          const imageUrl = resolveCharacterImageUrl(characterDraft);
          const storyData = await initializeStory(
            activeSession.threadId,
            activeSession.characterId,
            characterDraft.selectedScene.id,
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

      const initialMessages: GameMessage[] = [];
      if (storyData.story_background) {
        initialMessages.push({ role: 'assistant', content: storyData.story_background });
      }
      if (storyData.character_dialogue) {
        initialMessages.push({ role: 'assistant', content: storyData.character_dialogue });
      }
      actions.replaceMessages(initialMessages);
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
