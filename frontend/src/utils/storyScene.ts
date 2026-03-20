import { getSceneNameById } from '@/config/scenes';
import type {
  CheckEndingResponse,
  LegacyStoryEndingPayload,
  ProcessGameInputResponse,
  StoryHistoryItemPayload,
  StorySessionHistoryResponse,
  StoryEndingSummaryItemPayload,
  StoryEndingSummaryResponse,
  StoryResponsePayload,
  StorySessionSnapshotResponse,
} from '@/types/api';
import type {
  GameTurnResult,
  InitialGameData,
  PlayerOption,
  StoryEndingCheckResult,
  StoryEndingSummary,
  StoryEndingSummaryResult,
  StorySessionHistoryResult,
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

const normalizeOptionalMetric = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value.trim());
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return null;
};

const normalizeNumericRecord = (value: unknown): Record<string, number> => {
  const record = asRecord(value);
  if (!record) {
    return {};
  }

  return Object.entries(record).reduce<Record<string, number>>((normalized, [key, rawValue]) => {
    const metric = normalizeOptionalMetric(rawValue);
    if (metric === null) {
      return normalized;
    }

    normalized[key] = metric;
    return normalized;
  }, {});
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

const normalizeStoryEndingKeyStates = (value: unknown) => {
  const payload = asRecord(value);
  return {
    favorability: normalizeOptionalMetric(payload?.favorability),
    trust: normalizeOptionalMetric(payload?.trust),
    hostility: normalizeOptionalMetric(payload?.hostility),
    dependence: normalizeOptionalMetric(payload?.dependence),
  };
};

const normalizeLegacyStoryEndingPayload = (
  payload: Partial<LegacyStoryEndingPayload> | null | undefined
): StoryEndingCheckResult['ending'] | null => {
  const type = normalizeOptionalString(payload?.type);
  const description = normalizeOptionalString(payload?.description);

  if (!type || !description) {
    return null;
  }

  return {
    type,
    description,
    favorability: normalizeOptionalMetric(payload?.favorability),
    trust: normalizeOptionalMetric(payload?.trust),
    hostility: normalizeOptionalMetric(payload?.hostility),
  };
};

const normalizeStoryEndingSummaryItem = (
  payload: Partial<StoryEndingSummaryItemPayload> | null | undefined
): StoryEndingSummary | null => {
  const type = normalizeOptionalString(payload?.type);
  const description = normalizeOptionalString(payload?.description);

  if (!type || !description) {
    return null;
  }

  return {
    type,
    description,
    sceneId: normalizeOptionalString(payload?.scene),
    eventTitle: normalizeOptionalString(payload?.event_title),
    keyStates: normalizeStoryEndingKeyStates(payload?.key_states),
  };
};

export const normalizeStoryEndingCheckPayload = (
  payload: Partial<CheckEndingResponse> | null | undefined
): StoryEndingCheckResult => ({
  hasEnding: payload?.has_ending === true,
  ending: normalizeLegacyStoryEndingPayload(payload?.ending),
});

export const normalizeStoryEndingSummaryPayload = (
  payload: Partial<StoryEndingSummaryResponse> | null | undefined
): StoryEndingSummaryResult => ({
  threadId: normalizeOptionalString(payload?.thread_id) ?? '',
  status: normalizeOptionalString(payload?.status),
  roundNo: normalizeOptionalNumber(payload?.round_no),
  hasEnding: payload?.has_ending === true,
  ending: normalizeStoryEndingSummaryItem(payload?.ending),
  updatedAt: normalizeOptionalString(payload?.updated_at),
  expiresAt: normalizeOptionalString(payload?.expires_at),
});

const normalizeStoryHistoryItem = (
  payload: Partial<StoryHistoryItemPayload> | null | undefined
) => ({
  roundNo: normalizeOptionalNumber(payload?.round_no),
  status: normalizeOptionalString(payload?.status) ?? 'in_progress',
  sceneId: normalizeOptionalString(payload?.scene),
  eventTitle: normalizeOptionalString(payload?.event_title),
  characterDialogue: normalizeOptionalString(payload?.character_dialogue),
  userAction: {
    kind: normalizeOptionalString(payload?.user_action?.kind) ?? 'free_text',
    summary: normalizeOptionalString(payload?.user_action?.summary) ?? '',
    rawInput: normalizeOptionalString(payload?.user_action?.raw_input),
    optionIndex:
      payload?.user_action?.option_index === null
        ? null
        : normalizeOptionalNumber(payload?.user_action?.option_index, -1) >= 0
          ? normalizeOptionalNumber(payload?.user_action?.option_index)
          : null,
    optionText: normalizeOptionalString(payload?.user_action?.option_text),
    optionType: normalizeOptionalString(payload?.user_action?.option_type),
  },
  stateSummary: {
    changes: normalizeNumericRecord(payload?.state_summary?.changes),
    currentStates: normalizeNumericRecord(payload?.state_summary?.current_states),
  },
  isEventFinished: payload?.is_event_finished === true,
  isGameFinished: payload?.is_game_finished === true,
  createdAt: normalizeOptionalString(payload?.created_at),
});

export const normalizeStorySessionHistoryPayload = (
  payload: Partial<StorySessionHistoryResponse> | null | undefined
): StorySessionHistoryResult => ({
  threadId: normalizeOptionalString(payload?.thread_id) ?? '',
  status: normalizeOptionalString(payload?.status),
  currentRoundNo: normalizeOptionalNumber(payload?.current_round_no),
  latestSceneId: normalizeOptionalString(payload?.latest_scene),
  updatedAt: normalizeOptionalString(payload?.updated_at),
  expiresAt: normalizeOptionalString(payload?.expires_at),
  history: Array.isArray(payload?.history)
    ? payload.history.map((item) => normalizeStoryHistoryItem(item))
    : [],
});

export const toStoryEndingCheckResult = (
  payload: StoryEndingSummaryResult
): StoryEndingCheckResult => ({
  hasEnding: payload.hasEnding && payload.ending !== null,
  ending: payload.ending
    ? {
        type: payload.ending.type,
        description: payload.ending.description,
        favorability: payload.ending.keyStates.favorability,
        trust: payload.ending.keyStates.trust,
        hostility: payload.ending.keyStates.hostility,
      }
    : null,
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
    isGameFinished: storyScene.isGameFinished,
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
    isGameFinished: 'isGameFinished' in data ? data.isGameFinished === true : false,
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
