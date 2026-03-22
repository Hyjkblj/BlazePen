import { useCallback } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { persistStoryProgress, readStoryThreadSave } from '@/storage/storySessionCache';
import type { GameMessage, GameSessionSnapshot } from '@/types/game';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName } from '@/utils/storyScene';
import type { GameSessionInitActions } from './useGameState';

export interface RestoreLocalSaveOptions {
  characterId?: string | null;
  announce?: boolean;
}

export interface UseStorySessionSnapshotCacheOptions {
  actions: GameSessionInitActions;
  feedback: Pick<FeedbackContextValue, 'success' | 'error'>;
  setCharacterImage: (characterId: string | null) => void;
}

export interface UseStorySessionSnapshotCacheResult {
  loadGameSave: (threadId: string) => boolean;
  saveGameProgress: (
    threadId: string,
    messages: GameMessage[],
    characterId?: string,
    snapshot?: GameSessionSnapshot
  ) => void;
  restoreLocalSave: (
    threadId: string,
    options?: RestoreLocalSaveOptions
  ) => boolean;
}

export function useStorySessionSnapshotCache({
  actions,
  feedback,
  setCharacterImage,
}: UseStorySessionSnapshotCacheOptions): UseStorySessionSnapshotCacheResult {
  const restoreSavedSnapshot = useCallback(
    (snapshot: GameSessionSnapshot | undefined, characterId?: string | null) => {
      if (!snapshot) {
        actions.setGameFinished(false);
        if (characterId) {
          setCharacterImage(characterId);
        }
        return;
      }

      actions.setGameFinished(snapshot.isGameFinished === true);
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

  const restoreLocalSave = useCallback(
    (threadId: string, { characterId, announce = false }: RestoreLocalSaveOptions = {}) => {
      try {
        const save = readStoryThreadSave(threadId);
        if (!save) {
          return false;
        }

        const restoredMessages =
          Array.isArray(save.messages) && save.messages.length > 0
            ? save.messages
            : save.snapshot?.currentDialogue
              ? [{ role: 'assistant' as const, content: save.snapshot.currentDialogue }]
              : [];

        if (restoredMessages.length === 0 && !save.snapshot) {
          return false;
        }

        actions.replaceMessages(restoredMessages);
        restoreSavedSnapshot(save.snapshot, characterId ?? save.characterId ?? null);

        if (announce) {
          feedback.success('Save loaded.');
        }

        return true;
      } catch (error: unknown) {
        logger.error('failed to load save:', error);
        if (announce) {
          feedback.error('Failed to load save.');
        }
      }

      return false;
    },
    [actions, feedback, restoreSavedSnapshot]
  );

  const loadGameSave = useCallback(
    (threadId: string) => restoreLocalSave(threadId, { announce: true }),
    [restoreLocalSave]
  );

  const saveGameProgress = useCallback(
    (
      threadId: string,
      messages: GameMessage[],
      characterId?: string,
      snapshot?: GameSessionSnapshot
    ) => {
      try {
        persistStoryProgress({
          threadId,
          characterId,
          messages,
          snapshot,
        });
      } catch (error: unknown) {
        logger.error('failed to save progress:', error);
      }
    },
    []
  );

  return {
    loadGameSave,
    saveGameProgress,
    restoreLocalSave,
  };
}
