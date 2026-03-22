import { useCallback } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { getCharacterImages } from '@/services/characterApi';
import { getStorySessionSnapshot } from '@/services/gameApi';
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
import {
  getStorySessionLocalFallbackWarning,
  getStorySessionRestoreFailureMessage,
  isStorySessionLocalFallbackCandidate,
} from './storySessionRestoreExecutor';
import { useStorySessionSnapshotCache } from './useStorySessionSnapshotCache';

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

  const { loadGameSave, saveGameProgress, restoreLocalSave } = useStorySessionSnapshotCache({
    actions,
    feedback,
    setCharacterImage,
  });

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

        if (
          isStorySessionLocalFallbackCandidate(error) &&
          restoreLocalSave(threadId, { characterId, announce: false })
        ) {
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
      const warningMessage = getStorySessionLocalFallbackWarning(error);
      if (warningMessage) {
        feedback.warning(warningMessage);
      }
    },
    [feedback]
  );

  const notifyRestoreFailure = useCallback(
    (error: unknown, fallbackMessage: string) => {
      feedback.error(getStorySessionRestoreFailureMessage(error, fallbackMessage));
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
