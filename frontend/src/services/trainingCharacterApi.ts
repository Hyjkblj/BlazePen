import httpClient, { getErrorData, getErrorStatus, unwrapApiData } from '@/services/httpClient';
import { ServiceError, toServiceError } from '@/services/serviceError';
import type {
  ApiErrorData,
  CharacterImagesResponse,
  RemoveBackgroundResponse,
  TrainingCharacterPreviewJobCreateRequest,
  TrainingCharacterPreviewJobResponse,
  TrainingCreateCharacterRequest,
  TrainingCreateCharacterResponse,
  TrainingIdentityPresetApiResponse,
  TrainingIdentityPresetListResponse,
} from '@/types/api';
import type { CharacterCreationResult } from '@/types/game';
import { logger } from '@/utils/logger';

const PREVIEW_JOB_FINAL_STATUSES = new Set(['succeeded', 'failed']);
const PREVIEW_JOB_ACTIVE_STATUSES = new Set(['pending', 'running']);
const PREVIEW_CONFLICT_ERROR_CODE = 'TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT';

export type TrainingCharacterPreviewJobStatus = 'pending' | 'running' | 'succeeded' | 'failed';

export interface TrainingIdentityPresetOption {
  code: string;
  title: string;
  description: string;
  identity: string;
  defaultName: string;
  defaultGender: string;
}

export interface TrainingCharacterPreviewJobResult {
  jobId: string;
  characterId: string;
  idempotencyKey: string;
  status: TrainingCharacterPreviewJobStatus;
  imageUrls: string[];
  sceneStorylineScript?: Record<string, unknown>;
  sceneGroups?: Array<Record<string, unknown>>;
  sceneGenerationStatus?: TrainingCharacterPreviewJobStatus | 'skipped';
  sceneGenerationError?: string | null;
  sceneGeneratedAt?: string | null;
  attemptCount: number;
  lastFailedAt: string | null;
  lastErrorMessage: string | null;
  errorMessage: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

export interface WaitForTrainingCharacterPreviewJobOptions {
  pollIntervalMs?: number;
  timeoutMs?: number;
}

export interface TrainingCharacterBackgroundSelectionInput {
  imageUrl?: string;
  imageUrls?: string[];
  selectedIndex?: number;
}

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

const readStructuredError = (errorData: ApiErrorData | undefined): Record<string, unknown> | null => {
  if (!errorData || typeof errorData.error !== 'object' || errorData.error === null) {
    return null;
  }

  return errorData.error as Record<string, unknown>;
};

const readStructuredErrorCode = (errorData: ApiErrorData | undefined): string | null => {
  const structured = readStructuredError(errorData);
  const code = structured?.code;
  return typeof code === 'string' && code.trim() !== '' ? code.trim() : null;
};

const readStructuredErrorDetails = (errorData: ApiErrorData | undefined): unknown => {
  const structured = readStructuredError(errorData);
  if (structured?.details !== undefined) {
    return structured.details;
  }

  return errorData?.details ?? errorData?.detail ?? errorData?.error;
};

const readStructuredTraceId = (errorData: ApiErrorData | undefined): string | null => {
  const structured = readStructuredError(errorData);
  const traceId = structured?.traceId ?? structured?.trace_id ?? errorData?.traceId ?? errorData?.trace_id;
  return normalizeOptionalString(traceId);
};

const normalizeCharacterId = (value: unknown): string => {
  const normalized = normalizeOptionalString(
    typeof value === 'string' || typeof value === 'number' ? String(value) : null
  );
  return normalized ?? '';
};

const normalizeNonNegativeInteger = (value: unknown): number => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, Math.trunc(value));
  }

  const normalized = normalizeOptionalString(typeof value === 'string' ? value : null);
  if (!normalized) {
    return 0;
  }

  const parsed = Number.parseInt(normalized, 10);
  if (!Number.isInteger(parsed)) {
    return 0;
  }

  return Math.max(parsed, 0);
};

const normalizeStringArray = (value: unknown): string[] =>
  Array.isArray(value)
    ? value
        .filter((item): item is string => typeof item === 'string')
        .map((item) => item.trim())
        .filter((item) => item !== '')
    : [];

const normalizeTrainingPreviewJobStatus = (value: unknown): TrainingCharacterPreviewJobStatus => {
  const normalized = normalizeOptionalString(value)?.toLowerCase();
  if (normalized === 'pending' || normalized === 'running') {
    return normalized;
  }
  if (normalized === 'succeeded' || normalized === 'failed') {
    return normalized;
  }
  return 'pending';
};

const normalizeSceneGenerationStatus = (
  value: unknown
): TrainingCharacterPreviewJobStatus | 'skipped' => {
  const normalized = normalizeOptionalString(value)?.toLowerCase();
  if (normalized === 'pending' || normalized === 'running' || normalized === 'succeeded' || normalized === 'failed') {
    return normalized;
  }
  if (normalized === 'skipped') {
    return 'skipped';
  }
  return 'pending';
};

const normalizeRecord = (value: unknown): Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};

const normalizeRecordArray = (value: unknown): Array<Record<string, unknown>> =>
  Array.isArray(value)
    ? value
        .map((item) => normalizeRecord(item))
        .filter((item) => Object.keys(item).length > 0)
    : [];

const normalizeRemoveBackgroundResponse = (payload: unknown): RemoveBackgroundResponse => {
  const record = normalizeRecord(payload);

  return {
    original_url: normalizeOptionalString(record.original_url) ?? undefined,
    transparent_url: normalizeOptionalString(record.transparent_url) ?? undefined,
    selected_image_url: normalizeOptionalString(record.selected_image_url) ?? undefined,
  };
};

const normalizeCharacterCreationResult = (
  payload: TrainingCreateCharacterResponse | null | undefined
): CharacterCreationResult => ({
  characterId: normalizeCharacterId(payload?.character_id),
  name: normalizeOptionalString(payload?.name),
  imageUrl: normalizeOptionalString(payload?.image_url),
  imageUrls: normalizeStringArray(payload?.image_urls),
});

const normalizeTrainingIdentityPreset = (
  payload: TrainingIdentityPresetApiResponse
): TrainingIdentityPresetOption | null => {
  const code = normalizeOptionalString(payload?.code);
  if (!code) {
    return null;
  }

  return {
    code,
    title: normalizeOptionalString(payload?.title) ?? code,
    description: normalizeOptionalString(payload?.description) ?? '',
    identity: normalizeOptionalString(payload?.identity) ?? '',
    defaultName: normalizeOptionalString(payload?.default_name) ?? '',
    defaultGender: normalizeOptionalString(payload?.default_gender) ?? '',
  };
};

const normalizeTrainingCharacterPreviewJob = (
  payload: TrainingCharacterPreviewJobResponse | null | undefined
): TrainingCharacterPreviewJobResult => ({
  jobId: normalizeOptionalString(payload?.job_id) ?? '',
  characterId: normalizeCharacterId(payload?.character_id),
  idempotencyKey: normalizeOptionalString(payload?.idempotency_key) ?? '',
  status: normalizeTrainingPreviewJobStatus(payload?.status),
  imageUrls: normalizeStringArray(payload?.image_urls),
  sceneStorylineScript: normalizeRecord(payload?.scene_storyline_script),
  sceneGroups: normalizeRecordArray(payload?.scene_groups),
  sceneGenerationStatus: normalizeSceneGenerationStatus(payload?.scene_generation_status),
  sceneGenerationError: normalizeOptionalString(payload?.scene_generation_error),
  sceneGeneratedAt: normalizeOptionalString(payload?.scene_generated_at),
  attemptCount: normalizeNonNegativeInteger(payload?.attempt_count),
  lastFailedAt: normalizeOptionalString(payload?.last_failed_at),
  lastErrorMessage: normalizeOptionalString(payload?.last_error_message),
  errorMessage: normalizeOptionalString(payload?.error_message),
  createdAt: normalizeOptionalString(payload?.created_at),
  updatedAt: normalizeOptionalString(payload?.updated_at),
});

export const listTrainingIdentityPresets = async (): Promise<TrainingIdentityPresetOption[]> => {
  try {
    const response = await httpClient.get('/v1/training/characters/identity-presets', {
      timeout: 30000,
    });
    const payload = unwrapApiData<TrainingIdentityPresetListResponse>(response);
    const presets = Array.isArray(payload?.presets) ? payload.presets : [];
    return presets
      .map((item) => normalizeTrainingIdentityPreset(item))
      .filter((item): item is TrainingIdentityPresetOption => item !== null);
  } catch (error: unknown) {
    throw toServiceError(error, {
      fallbackMessage: 'Failed to load training identity presets.',
      timeoutMessage: 'Loading training identity presets timed out. Please retry.',
    });
  }
};

export const createTrainingCharacter = async (
  data: TrainingCreateCharacterRequest
): Promise<CharacterCreationResult> => {
  try {
    const response = await httpClient.post('/v1/training/characters/create', data, {
      timeout: 60000,
    });
    return normalizeCharacterCreationResult(unwrapApiData<TrainingCreateCharacterResponse>(response));
  } catch (error: unknown) {
    throw toServiceError(error, {
      fallbackMessage: 'Failed to create training character.',
      timeoutMessage: 'Training character creation timed out. Please retry in a moment.',
    });
  }
};

export const createTrainingCharacterPreviewJob = async (
  data: TrainingCharacterPreviewJobCreateRequest
): Promise<TrainingCharacterPreviewJobResult> => {
  try {
    const response = await httpClient.post('/v1/training/characters/preview-jobs', data, {
      timeout: 30000,
    });
    return normalizeTrainingCharacterPreviewJob(
      unwrapApiData<TrainingCharacterPreviewJobResponse>(response)
    );
  } catch (error: unknown) {
    const errorData = getErrorData(error);
    const backendErrorCode = readStructuredErrorCode(errorData);
    if (backendErrorCode === PREVIEW_CONFLICT_ERROR_CODE) {
      const status = getErrorStatus(error);
      const message =
        typeof errorData?.message === 'string' && errorData.message.trim() !== ''
          ? errorData.message.trim()
          : 'Failed to create training preview job.';
      throw new ServiceError({
        code: PREVIEW_CONFLICT_ERROR_CODE,
        status,
        message,
        details: readStructuredErrorDetails(errorData),
        traceId: readStructuredTraceId(errorData),
        cause: error,
      });
    }

    throw toServiceError(error, {
      fallbackMessage: 'Failed to create training preview job.',
      timeoutMessage: 'Creating training preview job timed out. Please retry.',
    });
  }
};

export const getTrainingCharacterPreviewJob = async (
  jobId: string
): Promise<TrainingCharacterPreviewJobResult> => {
  const normalizedJobId = normalizeOptionalString(jobId);
  if (!normalizedJobId) {
    throw new ServiceError({
      code: 'VALIDATION_ERROR',
      message: 'preview jobId is required.',
    });
  }

  try {
    const response = await httpClient.get(`/v1/training/characters/preview-jobs/${normalizedJobId}`, {
      timeout: 30000,
    });
    return normalizeTrainingCharacterPreviewJob(
      unwrapApiData<TrainingCharacterPreviewJobResponse>(response)
    );
  } catch (error: unknown) {
    throw toServiceError(error, {
      fallbackMessage: 'Failed to load training preview job.',
      timeoutMessage: 'Loading training preview job timed out. Please retry.',
    });
  }
};

export const waitForTrainingCharacterPreviewJob = async (
  jobId: string,
  options: WaitForTrainingCharacterPreviewJobOptions = {}
): Promise<TrainingCharacterPreviewJobResult> => {
  const pollIntervalMs = Math.max(Number(options.pollIntervalMs ?? 1500), 500);
  const timeoutMs = Math.max(Number(options.timeoutMs ?? 180000), 10000);
  const startedAt = Date.now();

  while (true) {
    const jobResult = await getTrainingCharacterPreviewJob(jobId);
    if (PREVIEW_JOB_FINAL_STATUSES.has(jobResult.status)) {
      return jobResult;
    }

    if (!PREVIEW_JOB_ACTIVE_STATUSES.has(jobResult.status)) {
      logger.warn('[training-character-api] unexpected preview job status', jobResult.status);
      return {
        ...jobResult,
        status: 'failed',
        errorMessage: jobResult.errorMessage ?? `unexpected preview job status: ${jobResult.status}`,
      };
    }

    if (Date.now() - startedAt >= timeoutMs) {
      throw new ServiceError({
        code: 'REQUEST_TIMEOUT',
        message: 'Training preview generation timed out. Please retry.',
        retryable: true,
      });
    }

    await new Promise<void>((resolve) => {
      globalThis.setTimeout(resolve, pollIntervalMs);
    });
  }
};

export const getTrainingCharacterImages = async (
  characterId: string
): Promise<CharacterImagesResponse> => {
  try {
    const response = await httpClient.get(`/v1/training/characters/${characterId}/images`, {
      timeout: 60000,
    });
    return unwrapApiData<CharacterImagesResponse>(response);
  } catch (error: unknown) {
    const serviceError = toServiceError(error, {
      fallbackMessage: 'Failed to load training character images.',
      timeoutMessage: 'Training character image fetch timed out. Please retry.',
    });
    logger.warn('[training-character-api] training character image request failed', serviceError);
    throw serviceError;
  }
};

export const removeTrainingCharacterBackground = async (
  characterId: string,
  params: TrainingCharacterBackgroundSelectionInput
): Promise<RemoveBackgroundResponse> => {
  try {
    const response = await httpClient.post(
      `/v1/training/characters/${characterId}/remove-background`,
      {
        image_url: params.imageUrl,
        image_urls: params.imageUrls,
        selected_index: params.selectedIndex,
      },
      { timeout: 60000 }
    );
    return normalizeRemoveBackgroundResponse(unwrapApiData<unknown>(response));
  } catch (error: unknown) {
    throw toServiceError(error, {
      fallbackMessage: 'Failed to persist selected training preview image.',
      timeoutMessage: 'Persisting selected training preview image timed out. Please retry.',
    });
  }
};
