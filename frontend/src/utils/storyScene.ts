import { getSceneNameById } from '@/config/scenes';
import type {
  ProcessGameInputResponse,
  StoryResponsePayload,
  StorySessionSnapshotResponse,
} from '@/types/api';
import type {
  GameTurnResult,
  InitialGameData,
  PlayerOption,
  StorySceneData,
  StorySessionSnapshotResult,
} from '@/types/game';
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

const asRecord = (value: unknown): Record<string, unknown> | null =>
  typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : null;

const readStoryPayloadField = (payload: unknown, field: string): unknown => {
  const record = asRecord(payload);
  if (record && record[field] !== undefined && record[field] !== null) {
    return record[field];
  }

  const snapshotRecord = asRecord(record?.snapshot);
  if (snapshotRecord && snapshotRecord[field] !== undefined && snapshotRecord[field] !== null) {
    return snapshotRecord[field];
  }

  return undefined;
};

const normalizeOptionalNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseInt(value.trim(), 10);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
};

export const normalizeStoryScenePayload = (
  payload: Partial<StoryResponsePayload> | null | undefined
): StorySceneData => ({
  sceneId: normalizeOptionalString(readStoryPayloadField(payload, 'scene')),
  sceneImageUrl: normalizeOptionalString(readStoryPayloadField(payload, 'scene_image_url')),
  compositeImageUrl: normalizeOptionalString(readStoryPayloadField(payload, 'composite_image_url')),
  storyBackground: normalizeOptionalString(readStoryPayloadField(payload, 'story_background')),
  characterDialogue: normalizeOptionalString(readStoryPayloadField(payload, 'character_dialogue')),
  playerOptions: normalizePlayerOptions(readStoryPayloadField(payload, 'player_options')),
  isGameFinished: readStoryPayloadField(payload, 'is_game_finished') === true,
});

export const normalizeStoryTurnPayload = (
  payload: Partial<ProcessGameInputResponse> | null | undefined
): GameTurnResult => ({
  threadId: normalizeOptionalString(payload?.thread_id),
  sessionRestored: payload?.session_restored === true,
  needReselectOption: payload?.need_reselect_option === true,
  restoredFromThreadId: normalizeOptionalString(payload?.restored_from_thread_id),
  ...normalizeStoryScenePayload(payload),
});

export const normalizeStorySessionSnapshotPayload = (
  payload: Partial<StorySessionSnapshotResponse> | null | undefined
): StorySessionSnapshotResult => ({
  ...normalizeStoryTurnPayload(payload),
  roundNo: normalizeOptionalNumber(readStoryPayloadField(payload, 'round_no')),
  status: normalizeOptionalString(readStoryPayloadField(payload, 'status')),
  updatedAt: normalizeOptionalString(readStoryPayloadField(payload, 'updated_at')),
  expiresAt: normalizeOptionalString(readStoryPayloadField(payload, 'expires_at')),
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
