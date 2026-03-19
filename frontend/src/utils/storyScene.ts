import { getSceneNameById } from '@/config/scenes';
import type { StoryResponsePayload } from '@/types/api';
import type { InitialGameData, PlayerOption, StorySceneData } from '@/types/game';
import { resolveStaticSceneImageFallback } from './sceneAssets';

interface LegacyInitialGameData {
  scene?: string | null;
  story_background?: string | null;
  character_dialogue?: string | null;
  player_options?: PlayerOption[] | null;
  composite_image_url?: string | null;
  scene_image_url?: string | null;
}

type InitialGameDataInput = Partial<InitialGameData & LegacyInitialGameData> | null | undefined;

const normalizeOptionalString = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  if (normalized === '' || normalized === 'null' || normalized === 'undefined') {
    return null;
  }

  return normalized;
};

const normalizePlayerOptions = (value: unknown): PlayerOption[] =>
  Array.isArray(value) ? value : [];

export const normalizeStoryScenePayload = (
  payload: Partial<StoryResponsePayload> | null | undefined
): StorySceneData => ({
  sceneId: normalizeOptionalString(payload?.scene),
  sceneImageUrl: normalizeOptionalString(payload?.scene_image_url),
  compositeImageUrl: normalizeOptionalString(payload?.composite_image_url),
  storyBackground: normalizeOptionalString(payload?.story_background),
  characterDialogue: normalizeOptionalString(payload?.character_dialogue),
  playerOptions: normalizePlayerOptions(payload?.player_options),
  isGameFinished: payload?.is_game_finished === true,
});

export const toInitialGameData = (
  payload: StorySceneData | Partial<StoryResponsePayload> | null | undefined
): InitialGameData => {
  const storyScene =
    payload &&
    ('sceneId' in payload ||
      'sceneImageUrl' in payload ||
      'compositeImageUrl' in payload ||
      'storyBackground' in payload ||
      'characterDialogue' in payload ||
      'playerOptions' in payload ||
      'isGameFinished' in payload)
      ? {
          sceneId: normalizeOptionalString(payload.sceneId),
          sceneImageUrl: normalizeOptionalString(payload.sceneImageUrl),
          compositeImageUrl: normalizeOptionalString(payload.compositeImageUrl),
          storyBackground: normalizeOptionalString(payload.storyBackground),
          characterDialogue: normalizeOptionalString(payload.characterDialogue),
          playerOptions: normalizePlayerOptions(payload.playerOptions),
          isGameFinished: payload.isGameFinished === true,
        }
      : normalizeStoryScenePayload(payload);

  return {
    sceneId: storyScene.sceneId,
    storyBackground: storyScene.storyBackground,
    characterDialogue: storyScene.characterDialogue,
    playerOptions: storyScene.playerOptions,
    compositeImageUrl: storyScene.compositeImageUrl,
    sceneImageUrl: storyScene.sceneImageUrl,
  };
};

export const normalizeInitialGameData = (data: InitialGameDataInput): InitialGameData | null => {
  if (!data || typeof data !== 'object') {
    return null;
  }

  return {
    sceneId: normalizeOptionalString('sceneId' in data ? data.sceneId : data.scene),
    storyBackground: normalizeOptionalString(
      'storyBackground' in data ? data.storyBackground : data.story_background
    ),
    characterDialogue: normalizeOptionalString(
      'characterDialogue' in data ? data.characterDialogue : data.character_dialogue
    ),
    playerOptions: normalizePlayerOptions('playerOptions' in data ? data.playerOptions : data.player_options),
    compositeImageUrl: normalizeOptionalString(
      'compositeImageUrl' in data ? data.compositeImageUrl : data.composite_image_url
    ),
    sceneImageUrl: normalizeOptionalString(
      'sceneImageUrl' in data ? data.sceneImageUrl : data.scene_image_url
    ),
  };
};

export const resolveSceneDisplayName = (sceneId: string | null): string | null =>
  sceneId ? getSceneNameById(sceneId) : null;

export const resolveSceneImageAsset = (
  sceneId: string | null,
  explicitSceneImageUrl: string | null
): string | null => {
  if (explicitSceneImageUrl) {
    return explicitSceneImageUrl;
  }

  if (!sceneId) {
    return null;
  }

  return resolveStaticSceneImageFallback(sceneId);
};

export const resolveStorySceneVisual = (
  storyScene: Pick<StorySceneData, 'sceneId' | 'sceneImageUrl' | 'compositeImageUrl'>
):
  | { kind: 'composite'; imageUrl: string }
  | { kind: 'scene'; imageUrl: string | null } => {
  if (storyScene.compositeImageUrl) {
    return {
      kind: 'composite',
      imageUrl: storyScene.compositeImageUrl,
    };
  }

  return {
    kind: 'scene',
    imageUrl: resolveSceneImageAsset(storyScene.sceneId, storyScene.sceneImageUrl),
  };
};
