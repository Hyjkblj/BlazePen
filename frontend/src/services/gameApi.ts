import httpClient, { getErrorData, getErrorStatus, unwrapApiData } from '@/services/httpClient';
import type { ServiceErrorCode } from '@/services/serviceError';
import { ServiceError, toServiceError } from '@/services/serviceError';
import type {
  ApiErrorData,
  GameInitResponse,
  GetScenesResponse,
  InitializeStoryResponse,
  ProcessGameInputResponse,
  SceneApiItem,
  StorySessionHistoryResponse,
  StoryEndingSummaryResponse,
  StorySessionSnapshotResponse,
} from '@/types/api';
import type {
  GameTurnResult,
  StoryEndingCheckResult,
  StoryEndingSummaryResult,
  StorySessionHistoryResult,
  StorySceneData,
  StorySessionInitParams,
  StorySessionInitResult,
  StorySessionSnapshotResult,
  StoryTurnSubmitParams,
} from '@/types/game';
import {
  normalizeStoryEndingSummaryPayload,
  normalizeStoryScenePayload,
  normalizeStorySessionHistoryPayload,
  normalizeStorySessionSnapshotPayload,
  normalizeStoryTurnPayload,
  toStoryEndingCheckResult,
} from '@/utils/storyScene';
import { logger } from '@/utils/logger';

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

const STORY_SESSION_ERROR_CODES = new Set<ServiceErrorCode>([
  'STORY_SESSION_NOT_FOUND',
  'STORY_SESSION_EXPIRED',
  'STORY_SESSION_RESTORE_FAILED',
]);

const mapStorySessionErrorCode = (backendErrorCode: string | null): ServiceErrorCode | null => {
  if (!backendErrorCode || !STORY_SESSION_ERROR_CODES.has(backendErrorCode as ServiceErrorCode)) {
    return null;
  }

  return backendErrorCode as ServiceErrorCode;
};

const readStructuredError = (errorData: ApiErrorData | undefined): Record<string, unknown> | null => {
  if (!errorData || typeof errorData.error !== 'object' || errorData.error === null) {
    return null;
  }

  return errorData.error as Record<string, unknown>;
};

const readStructuredErrorCode = (errorData: ApiErrorData | undefined): string | null => {
  const structuredError = readStructuredError(errorData);
  const code = structuredError?.code;
  return typeof code === 'string' && code.trim() !== '' ? code.trim() : null;
};

const readStructuredErrorDetails = (errorData: ApiErrorData | undefined): unknown => {
  const structuredError = readStructuredError(errorData);
  if (structuredError?.details !== undefined) {
    return structuredError.details;
  }

  return errorData?.details ?? errorData?.detail ?? errorData?.error;
};

const readStructuredTraceId = (errorData: ApiErrorData | undefined): string | null => {
  const structuredError = readStructuredError(errorData);
  const structuredTraceId =
    structuredError?.traceId ?? structuredError?.trace_id ?? errorData?.traceId ?? errorData?.trace_id;

  return normalizeOptionalString(structuredTraceId);
};

const toStoryServiceError = (
  error: unknown,
  fallbackMessage: string,
  timeoutMessage: string
): ServiceError => {
  const status = getErrorStatus(error);
  const errorData = getErrorData(error);
  const backendErrorCode = readStructuredErrorCode(errorData);
  const rawMessage =
    typeof errorData?.message === 'string' && errorData.message.trim() !== ''
      ? errorData.message.trim()
      : fallbackMessage;
  const mappedStoryErrorCode = mapStorySessionErrorCode(backendErrorCode);

  if (mappedStoryErrorCode) {
    return new ServiceError({
      code: mappedStoryErrorCode,
      status,
      message: rawMessage,
      details: readStructuredErrorDetails(errorData),
      traceId: readStructuredTraceId(errorData),
      cause: error,
    });
  }

  return toServiceError(error, {
    fallbackMessage,
    timeoutMessage,
  });
};

const normalizeInitGameResponse = (
  payload: GameInitResponse | null | undefined
): StorySessionInitResult => {
  const threadId = normalizeOptionalString(payload?.thread_id);
  if (!threadId) {
    throw new ServiceError({
      code: 'INVALID_RESPONSE',
      message: 'Missing threadId in story session init response.',
    });
  }

  return {
    threadId,
    userId: normalizeOptionalString(payload?.user_id),
    gameMode: normalizeOptionalString(payload?.game_mode),
  };
};

export const initGame = async (
  data: StorySessionInitParams
): Promise<StorySessionInitResult> => {
  try {
    const response = await httpClient.post(
      '/v1/game/init',
      {
        user_id: data.userId,
        game_mode: data.gameMode ?? 'solo',
        character_id: data.characterId,
      },
      { timeout: 60000 }
    );
    return normalizeInitGameResponse(unwrapApiData<GameInitResponse>(response));
  } catch (error: unknown) {
    throw toStoryServiceError(
      error,
      'Failed to initialize story session.',
      'Story initialization timed out.'
    );
  }
};

export const initializeStory = async (
  threadId: string,
  characterId: string,
  sceneId?: string,
  characterImageUrl?: string
): Promise<StorySceneData> => {
  if (!threadId || !characterId) {
    throw new ServiceError({
      code: 'VALIDATION_ERROR',
      message: `Missing required params: threadId=${threadId}, characterId=${characterId}`,
    });
  }

  try {
    const response = await httpClient.post(
      '/v1/characters/initialize-story',
      {
        thread_id: threadId,
        character_id: String(characterId),
        scene_id: sceneId || 'school',
        character_image_url: characterImageUrl || undefined,
      },
      { timeout: 60000 }
    );
    return normalizeStoryScenePayload(unwrapApiData<InitializeStoryResponse>(response));
  } catch (error: unknown) {
    throw toStoryServiceError(
      error,
      'Failed to initialize story scene.',
      'Story scene initialization timed out.'
    );
  }
};

export const getScenes = async (): Promise<SceneApiItem[]> => {
  try {
    const response = await httpClient.get('/v1/characters/scenes');
    const payload = unwrapApiData<GetScenesResponse>(response);
    return Array.isArray(payload.scenes) ? payload.scenes : [];
  } catch (error: unknown) {
    const serviceError = toServiceError(error, {
      fallbackMessage: 'Failed to load story scenes.',
    });

    logger.error('[story-api] failed to fetch scenes', serviceError);
    throw serviceError;
  }
};

export const processGameInput = async (
  data: StoryTurnSubmitParams
): Promise<GameTurnResult> => {
  try {
    const response = await httpClient.post(
      '/v1/game/input',
      {
        thread_id: data.threadId,
        user_input: data.userInput,
        user_id: data.userId,
        character_id: data.characterId,
      },
      { timeout: 90000 }
    );
    return normalizeStoryTurnPayload(unwrapApiData<ProcessGameInputResponse>(response));
  } catch (error: unknown) {
    const serviceError = toStoryServiceError(
      error,
      'Failed to process story turn.',
      'Story turn processing timed out.'
    );

    if (
      serviceError.code === 'STORY_SESSION_EXPIRED' ||
      serviceError.code === 'STORY_SESSION_NOT_FOUND'
    ) {
      logger.warn('[story-api] story session expired during turn submission');
    }

    throw serviceError;
  }
};

export const getStorySessionSnapshot = async (
  threadId: string
): Promise<StorySessionSnapshotResult> => {
  const normalizedThreadId = normalizeOptionalString(threadId);
  if (!normalizedThreadId) {
    throw new ServiceError({
      code: 'VALIDATION_ERROR',
      message: 'Missing threadId for story session snapshot request.',
    });
  }

  try {
    const response = await httpClient.get(`/v1/game/sessions/${normalizedThreadId}`, {
      timeout: 30000,
    });
    return normalizeStorySessionSnapshotPayload(
      unwrapApiData<StorySessionSnapshotResponse>(response)
    );
  } catch (error: unknown) {
    throw toStoryServiceError(
      error,
      'Failed to restore story session snapshot.',
      'Story session restore timed out.'
    );
  }
};

export const getStoryEndingSummary = async (
  threadId: string
): Promise<StoryEndingSummaryResult> => {
  const normalizedThreadId = normalizeOptionalString(threadId);
  if (!normalizedThreadId) {
    throw new ServiceError({
      code: 'VALIDATION_ERROR',
      message: 'Missing threadId for story ending summary request.',
    });
  }

  try {
    const response = await httpClient.get(`/v1/game/sessions/${normalizedThreadId}/ending`, {
      timeout: 30000,
    });
    const endingSummary = normalizeStoryEndingSummaryPayload(
      unwrapApiData<StoryEndingSummaryResponse>(response)
    );

    if (!endingSummary.threadId) {
      throw new ServiceError({
        code: 'INVALID_RESPONSE',
        message: 'Missing threadId in story ending summary response.',
      });
    }

    return endingSummary;
  } catch (error: unknown) {
    throw toStoryServiceError(
      error,
      'Failed to load story ending summary.',
      'Ending summary timed out.'
    );
  }
};

export const getStorySessionHistory = async (
  threadId: string
): Promise<StorySessionHistoryResult> => {
  const normalizedThreadId = normalizeOptionalString(threadId);
  if (!normalizedThreadId) {
    throw new ServiceError({
      code: 'VALIDATION_ERROR',
      message: 'Missing threadId for story history request.',
    });
  }

  try {
    const response = await httpClient.get(`/v1/game/sessions/${normalizedThreadId}/history`, {
      timeout: 30000,
    });
    const historyResult = normalizeStorySessionHistoryPayload(
      unwrapApiData<StorySessionHistoryResponse>(response)
    );

    if (!historyResult.threadId) {
      throw new ServiceError({
        code: 'INVALID_RESPONSE',
        message: 'Missing threadId in story history response.',
      });
    }

    return historyResult;
  } catch (error: unknown) {
    throw toStoryServiceError(
      error,
      'Failed to load story history.',
      'Story history request timed out.'
    );
  }
};

export const checkEnding = async (threadId: string): Promise<StoryEndingCheckResult> => {
  const endingSummary = await getStoryEndingSummary(threadId);
  return toStoryEndingCheckResult(endingSummary);
};

export const triggerEnding = async (threadId: string): Promise<GameTurnResult> => {
  try {
    const response = await httpClient.post('/v1/game/trigger-ending', { thread_id: threadId });
    return normalizeStoryTurnPayload(unwrapApiData<ProcessGameInputResponse>(response));
  } catch (error: unknown) {
    throw toStoryServiceError(
      error,
      'Failed to trigger story ending.',
      'Ending trigger timed out.'
    );
  }
};
