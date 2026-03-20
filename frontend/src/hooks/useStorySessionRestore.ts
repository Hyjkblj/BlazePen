import { useCallback } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { getCharacterImages } from '@/services/characterApi';
import { getStorySessionSnapshot } from '@/services/gameApi';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import { persistStoryProgress, readStoryThreadSave } from '@/storage/storySessionCache';
import type {
  CharacterData,
  GameMessage,
  GameSessionSnapshot,
  InitialGameData,
  StorySceneData,
} from '@/types/game';
import { resolveCharacterImageUrl } from '@/utils/game';
import {
  buildInitialAssistantMessages,
  hasStorySceneVisual,
  type SelectedSceneTransition,
} from '@/utils/gameSession';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName, resolveStorySceneVisual } from '@/utils/storyScene';
import type { GameSessionInitActions, SceneTransitionMode } from './useGameState';

interface RestoreLocalSaveOptions {
  characterId?: string | null;
  announce?: boolean;
}

export interface StorySessionRestoreResult {
  restored: boolean;
  source: 'server' | 'local' | 'none';
  error?: unknown;
}

export interface UseStorySessionRestoreOptions {
  actions: GameSessionInitActions;
  feedback: Pick<FeedbackContextValue, 'success' | 'error' | 'warning'>;
  characterDraft: CharacterData | null;
}

export interface UseStorySessionRestoreResult {
  loadGameSave: (threadId: string) => boolean;
  saveGameProgress: (
    threadId: string,
    messages: GameMessage[],
    characterId?: string,
    snapshot?: GameSessionSnapshot
  ) => void;
  setCharacterImage: (characterId: string | null) => void;
  applyStoryData: (
    storyData: InitialGameData | StorySceneData,
    options?: {
      characterId?: string | null;
      sceneMode?: SceneTransitionMode;
    }
  ) => void;
  applyInitialEntryData: (
    storyData: InitialGameData,
    options: {
      characterId: string | null;
      selectedSceneTransition: SelectedSceneTransition | null;
    }
  ) => void;
  restoreFromServerSnapshot: (
    threadId: string,
    characterId: string | null
  ) => Promise<StorySessionRestoreResult>;
  notifyLocalRestoreFallback: (error: unknown) => void;
  notifyRestoreFailure: (error: unknown, fallbackMessage: string) => void;
}

const canUseLocalSnapshotFallback = (error: unknown) =>
  isServiceError(error) &&
  (error.code === 'REQUEST_TIMEOUT' || error.code === 'SERVICE_UNAVAILABLE');

export function useStorySessionRestore({
  actions,
  feedback,
  characterDraft,
}: UseStorySessionRestoreOptions): UseStorySessionRestoreResult {
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
      const imageUrl = resolveCharacterImageUrl(characterDraft);
      if (imageUrl) {
        actions.setCharacterImageUrl(imageUrl);
        return;
      }

      loadCharacterImageFromAPI(characterId);
    },
    [actions, characterDraft, loadCharacterImageFromAPI]
  );

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

  const applyStoryData = useCallback(
    (
      storyData: InitialGameData | StorySceneData,
      {
        characterId,
        sceneMode = 'silent',
      }: {
        characterId?: string | null;
        sceneMode?: SceneTransitionMode;
      } = {}
    ) => {
      if (storyData.sceneId) {
        actions.enterScene(
          storyData.sceneId,
          resolveSceneDisplayName(storyData.sceneId) ?? storyData.sceneId,
          sceneMode
        );
      }

      const visual = resolveStorySceneVisual(storyData);
      if (visual.kind === 'composite') {
        actions.applyCompositeScene(visual.imageUrl);
      } else if (hasStorySceneVisual(storyData)) {
        actions.applySceneVisual({
          sceneImageUrl: visual.imageUrl,
          clearCharacterImage: !characterId,
        });
        setCharacterImage(characterId ?? null);
      } else {
        actions.applySceneVisual({ sceneImageUrl: null });
      }

      actions.setDialogue(storyData.characterDialogue);
      actions.setOptions(storyData.playerOptions);
      actions.setGameFinished(storyData.isGameFinished);
    },
    [actions, setCharacterImage]
  );

  const applyServerSnapshot = useCallback(
    (
      snapshot: StorySceneData & {
        storyBackground: string | null;
        characterDialogue: string | null;
        playerOptions: StorySceneData['playerOptions'];
      },
      characterId?: string | null
    ) => {
      actions.replaceMessages(buildInitialAssistantMessages(snapshot));
      applyStoryData(snapshot, { characterId, sceneMode: 'silent' });
    },
    [actions, applyStoryData]
  );

  const restoreFromServerSnapshot = useCallback(
    async (threadId: string, characterId: string | null): Promise<StorySessionRestoreResult> => {
      try {
        const snapshot = await getStorySessionSnapshot(threadId);
        applyServerSnapshot(snapshot, characterId);
        return {
          restored: true,
          source: 'server',
        };
      } catch (error: unknown) {
        logger.warn(`[game] failed to load server snapshot for ${threadId}`, error);

        if (canUseLocalSnapshotFallback(error) && restoreLocalSave(threadId, { characterId, announce: false })) {
          return {
            restored: true,
            source: 'local',
            error,
          };
        }

        return {
          restored: false,
          source: 'none',
          error,
        };
      }
    },
    [applyServerSnapshot, restoreLocalSave]
  );

  const notifyLocalRestoreFallback = useCallback(
    (error: unknown) => {
      if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
        feedback.warning(
          'Server restore timed out. Loaded the last local story snapshot in read-only mode.'
        );
        return;
      }

      if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
        feedback.warning(
          'Story restore service is unavailable. Loaded the last local story snapshot in read-only mode.'
        );
      }
    },
    [feedback]
  );

  const notifyRestoreFailure = useCallback(
    (error: unknown, fallbackMessage: string) => {
      if (isServiceError(error) && error.code === 'STORY_SESSION_NOT_FOUND') {
        feedback.error('Story session could not be found. Please restart the story.');
        return;
      }

      if (
        isServiceError(error) &&
        (error.code === 'STORY_SESSION_EXPIRED' || error.code === 'SESSION_EXPIRED')
      ) {
        feedback.error('Story session expired. Please restart the story.');
        return;
      }

      if (isServiceError(error) && error.code === 'STORY_SESSION_RESTORE_FAILED') {
        feedback.error('Story session recovery failed. Please restart the story.');
        return;
      }

      if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
        feedback.error('Story session restore timed out. Please retry.');
        return;
      }

      feedback.error(getServiceErrorMessage(error, fallbackMessage));
    },
    [feedback]
  );

  const applyInitialEntryData = useCallback(
    (
      storyData: InitialGameData,
      {
        characterId,
        selectedSceneTransition,
      }: {
        characterId: string | null;
        selectedSceneTransition: SelectedSceneTransition | null;
      }
    ) => {
      const hasInitialVisual = hasStorySceneVisual(storyData);

      if (hasInitialVisual) {
        applyStoryData(storyData, { characterId, sceneMode: 'silent' });
      } else if (selectedSceneTransition) {
        actions.enterScene(
          selectedSceneTransition.sceneId,
          selectedSceneTransition.sceneName,
          'reset'
        );
      }

      actions.replaceMessages(buildInitialAssistantMessages(storyData));

      if (!hasInitialVisual) {
        setCharacterImage(characterId);
      }
    },
    [actions, applyStoryData, setCharacterImage]
  );

  return {
    loadGameSave,
    saveGameProgress,
    setCharacterImage,
    applyStoryData,
    applyInitialEntryData,
    restoreFromServerSnapshot,
    notifyLocalRestoreFallback,
    notifyRestoreFailure,
  };
}
