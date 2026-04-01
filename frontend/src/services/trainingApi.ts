import httpClient, { getErrorData, getErrorStatus, unwrapApiData } from '@/services/httpClient';
import type { ServiceErrorCode } from '@/services/serviceError';
import { ServiceError, toServiceError } from '@/services/serviceError';
import type {
  ApiErrorData,
  TrainingDiagnosticsResponse,
  TrainingInitRequest,
  TrainingInitResponse,
  TrainingMediaTaskApiResponse,
  TrainingMediaTaskCreateRequest,
  TrainingMediaTaskListResponse,
  TrainingProgressResponse,
  TrainingReportResponse,
  TrainingRoundSubmitMediaTaskRequest,
  TrainingRoundSubmitRequest,
  TrainingRoundSubmitResponse,
  TrainingScenarioNextRequest,
  TrainingScenarioNextResponse,
  TrainingSessionSummaryResponse,
} from '@/types/api';
import type {
  TrainingDiagnosticsResult,
  TrainingInitResult,
  TrainingMediaTaskCreateParams,
  TrainingMediaTaskListParams,
  TrainingMediaTaskListResult,
  TrainingMediaTaskResult,
  TrainingProgressResult,
  TrainingReportResult,
  TrainingSessionSummaryResult,
  TrainingRoundSubmitParams,
  TrainingRoundSubmitResult,
  TrainingScenarioNextParams,
  TrainingScenarioNextResult,
  TrainingSessionInitParams,
} from '@/types/training';
import type { TrainingScenario } from '@/types/training';
import {
  normalizeTrainingDiagnosticsPayload,
  normalizeTrainingInitPayload,
  normalizeTrainingMediaTaskListPayload,
  normalizeTrainingMediaTaskPayload,
  normalizeTrainingMode,
  normalizeTrainingProgressPayload,
  normalizeTrainingReportPayload,
  normalizeTrainingRoundSubmitPayload,
  normalizeTrainingScenarioNextPayload,
  normalizeTrainingSessionSummaryPayload,
} from '@/utils/trainingSession';
import { logger } from '@/utils/logger';

const TRAINING_ERROR_CODES = new Set<ServiceErrorCode>([
  'TRAINING_SESSION_NOT_FOUND',
  'TRAINING_SESSION_COMPLETED',
  'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
  'TRAINING_ROUND_DUPLICATE',
  'TRAINING_MODE_UNSUPPORTED',
  'TRAINING_SCENARIO_MISMATCH',
  'TRAINING_MEDIA_TASK_NOT_FOUND',
  'TRAINING_MEDIA_TASK_INVALID',
  'TRAINING_MEDIA_TASK_CONFLICT',
  'TRAINING_MEDIA_TASK_UNSUPPORTED',
  'TRAINING_MEDIA_PROVIDER_UNAVAILABLE',
  'TRAINING_MEDIA_TASK_EXECUTION_FAILED',
  'TRAINING_MEDIA_TASK_TIMEOUT',
  'TRAINING_STORAGE_UNAVAILABLE',
]);

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
  const traceId =
    structuredError?.traceId ?? structuredError?.trace_id ?? errorData?.traceId ?? errorData?.trace_id;

  return normalizeOptionalString(traceId);
};

type TrainingMediaTaskConflictDetails = {
  existingTaskId: string;
  scope: {
    sessionId: string | null;
    roundNo: number | null;
  };
  idempotencyKey: string | null;
};

const normalizeTrainingMediaTaskConflictDetails = (
  details: unknown
): TrainingMediaTaskConflictDetails | null => {
  if (!details || typeof details !== 'object' || Array.isArray(details)) {
    return null;
  }
  const record = details as Record<string, unknown>;
  const existingTaskId =
    normalizeOptionalString(
      record.existingTaskId ??
        record.existing_task_id ??
        record.taskId ??
        record.task_id
    ) ?? '';
  if (!existingTaskId) {
    return null;
  }

  const sessionId = normalizeOptionalString(record.sessionId ?? record.session_id) ?? null;
  const scopeRecord =
    (record.scope ?? record.existing_scope ?? record.existingScope ?? record.existing) as
      | Record<string, unknown>
      | null
      | undefined;
  const roundNoValue =
    scopeRecord?.roundNo ??
    scopeRecord?.round_no ??
    record.roundNo ??
    record.round_no;
  const roundNo =
    typeof roundNoValue === 'number' && Number.isFinite(roundNoValue)
      ? roundNoValue
      : typeof roundNoValue === 'string' && roundNoValue.trim() !== ''
        ? Number(roundNoValue)
        : null;

  const idempotencyKey =
    normalizeOptionalString(record.idempotencyKey ?? record.idempotency_key) ?? null;

  return {
    existingTaskId,
    scope: {
      sessionId,
      roundNo: Number.isFinite(roundNo as number) ? (roundNo as number) : null,
    },
    idempotencyKey,
  };
};

const mapTrainingErrorCode = (backendErrorCode: string | null): ServiceErrorCode | null => {
  if (!backendErrorCode || !TRAINING_ERROR_CODES.has(backendErrorCode as ServiceErrorCode)) {
    return null;
  }

  return backendErrorCode as ServiceErrorCode;
};

const toTrainingServiceError = (
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
  const mappedErrorCode = mapTrainingErrorCode(backendErrorCode);

  if (mappedErrorCode) {
    const rawDetails = readStructuredErrorDetails(errorData);
    const normalizedDetails =
      mappedErrorCode === 'TRAINING_MEDIA_TASK_CONFLICT'
        ? normalizeTrainingMediaTaskConflictDetails(rawDetails) ?? rawDetails
        : rawDetails;
    return new ServiceError({
      code: mappedErrorCode,
      status,
      message: rawMessage,
      details: normalizedDetails,
      traceId: readStructuredTraceId(errorData),
      cause: error,
    });
  }

  return toServiceError(error, {
    fallbackMessage,
    timeoutMessage,
  });
};

const requireString = (value: unknown, fieldName: string): string => {
  const normalized = normalizeOptionalString(value);
  if (!normalized) {
    throw new ServiceError({
      code: 'VALIDATION_ERROR',
      message: `Missing ${fieldName} for training request.`,
    });
  }

  return normalized;
};

const normalizeCharacterId = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') {
    return undefined;
  }

  if (typeof value === 'number' && Number.isInteger(value) && value > 0) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseInt(value.trim(), 10);
    if (Number.isInteger(parsed) && parsed > 0) {
      return parsed;
    }
  }

  throw new ServiceError({
    code: 'VALIDATION_ERROR',
    message: 'characterId must be a positive integer when initializing training.',
  });
};

const TRAINING_MEDIA_TASK_TYPES = new Set(['image', 'tts', 'text']);

const normalizeTrainingMediaTaskType = (value: unknown): 'image' | 'tts' | 'text' => {
  const taskType = normalizeOptionalString(value)?.toLowerCase();
  if (taskType && TRAINING_MEDIA_TASK_TYPES.has(taskType)) {
    return taskType as 'image' | 'tts' | 'text';
  }

  throw new ServiceError({
    code: 'VALIDATION_ERROR',
    message: 'media task type must be one of image, tts, text.',
  });
};

const normalizeTrainingMediaTaskMaxRetries = (value: unknown): number => {
  if (value === null || value === undefined || value === '') {
    return 0;
  }

  if (typeof value === 'number' && Number.isInteger(value) && value >= 0) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseInt(value.trim(), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
      return parsed;
    }
  }

  throw new ServiceError({
    code: 'VALIDATION_ERROR',
    message: 'media task maxRetries must be a non-negative integer.',
  });
};

const normalizeTrainingMediaTaskRoundNo = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') {
    return undefined;
  }

  if (typeof value === 'number' && Number.isInteger(value) && value >= 0) {
    return value;
  }

  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number.parseInt(value.trim(), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
      return parsed;
    }
  }

  throw new ServiceError({
    code: 'VALIDATION_ERROR',
    message: 'media task roundNo must be a non-negative integer.',
  });
};

const buildTrainingSceneImagePrompt = (scenario: TrainingScenario): string =>
  [
    `Scene title: ${scenario.title || 'Untitled scene'}`,
    `Era: ${scenario.eraDate || 'Unknown era'}`,
    `Location: ${scenario.location || 'Unknown location'}`,
    `Brief: ${scenario.brief || 'N/A'}`,
    `Mission: ${scenario.mission || 'N/A'}`,
    `Decision focus: ${scenario.decisionFocus || 'N/A'}`,
  ].join('\n');

export const buildTrainingSceneImageMediaTaskCreateParams = (options: {
  sessionId: string;
  roundNo: number;
  scenario: TrainingScenario;
  attemptNo?: number;
  generateStorylineSeries?: boolean;
}): TrainingMediaTaskCreateParams => {
  const attemptNo = Math.max(0, Math.floor(options.attemptNo ?? 0));
  const idempotencyKey = `training-scene-image:${options.sessionId}:${options.scenario.id}:attempt:${attemptNo}`;
  const prompt = buildTrainingSceneImagePrompt(options.scenario);

  const payload: Record<string, unknown> = {
    session_id: options.sessionId,
    round_no: options.roundNo,
    scenario_id: options.scenario.id,
    scenario_title: options.scenario.title,
    major_scene_title: options.scenario.title,
    prompt,
    scenario_prompt: prompt,
    brief: options.scenario.brief,
    mission: options.scenario.mission,
    decision_focus: options.scenario.decisionFocus,
    image_type: 'scene',
  };

  // Default: do NOT force storyline-series generation from frontend hot path.
  if (options.generateStorylineSeries === true) {
    payload.generate_storyline_series = true;
  }

  return {
    sessionId: options.sessionId,
    roundNo: options.roundNo,
    taskType: 'image',
    idempotencyKey,
    maxRetries: 1,
    payload,
  };
};

const normalizeTrainingRoundSubmitMediaTasks = (
  mediaTasks: TrainingRoundSubmitParams['mediaTasks']
): TrainingRoundSubmitMediaTaskRequest[] | undefined => {
  if (!Array.isArray(mediaTasks) || mediaTasks.length === 0) {
    return undefined;
  }

  return mediaTasks.map((task) => ({
    task_type: normalizeTrainingMediaTaskType(task?.taskType),
    payload:
      task?.payload !== null &&
      typeof task?.payload === 'object' &&
      !Array.isArray(task.payload)
        ? { ...task.payload }
        : {},
    max_retries: normalizeTrainingMediaTaskMaxRetries(task?.maxRetries),
  }));
};

const normalizeTrainingMediaTaskPayloadObject = (payload: unknown): Record<string, unknown> => {
  if (payload !== null && typeof payload === 'object' && !Array.isArray(payload)) {
    return { ...(payload as Record<string, unknown>) };
  }
  return {};
};

const assertSessionId = (sessionId: string | null, routeName: string): string => {
  if (!sessionId) {
    throw new ServiceError({
      code: 'INVALID_RESPONSE',
      message: `Missing sessionId in ${routeName} response.`,
    });
  }

  return sessionId;
};

export const initTraining = async (
  params: TrainingSessionInitParams
): Promise<TrainingInitResult> => {
  const trainingMode = normalizeTrainingMode(params.trainingMode);
  const requestPayload: TrainingInitRequest = {
    user_id: requireString(params.userId, 'userId'),
    training_mode: trainingMode,
  };

  const characterId = normalizeCharacterId(params.characterId);
  if (characterId !== undefined) {
    requestPayload.character_id = characterId;
  }

  if (params.playerProfile) {
    requestPayload.player_profile = {
      name: normalizeOptionalString(params.playerProfile.name),
      gender: normalizeOptionalString(params.playerProfile.gender),
      identity: normalizeOptionalString(params.playerProfile.identity),
      age: params.playerProfile.age ?? null,
    };
  }

  try {
    const response = await httpClient.post('/v1/training/init', requestPayload, {
      timeout: 60000,
    });
    const result = normalizeTrainingInitPayload(
      unwrapApiData<TrainingInitResponse>(response),
      trainingMode
    );

    assertSessionId(result.sessionId, 'training init');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to initialize training session.',
      'Training initialization timed out.'
    );
  }
};

export const getNextTrainingScenario = async (
  params: TrainingScenarioNextParams
): Promise<TrainingScenarioNextResult> => {
  const requestPayload: TrainingScenarioNextRequest = {
    session_id: requireString(params.sessionId, 'sessionId'),
  };

  try {
    const response = await httpClient.post('/v1/training/scenario/next', requestPayload, {
      timeout: 30000,
    });
    const result = normalizeTrainingScenarioNextPayload(
      unwrapApiData<TrainingScenarioNextResponse>(response)
    );

    assertSessionId(result.sessionId, 'training scenario next');
    return result;
  } catch (error: unknown) {
    const serviceError = toTrainingServiceError(
      error,
      'Failed to load next training scenario.',
      'Loading the next training scenario timed out.'
    );

    if (serviceError.code === 'TRAINING_SESSION_NOT_FOUND') {
      logger.warn('[training-api] training session not found during scenario lookup');
    }

    throw serviceError;
  }
};

export const submitTrainingRound = async (
  params: TrainingRoundSubmitParams
): Promise<TrainingRoundSubmitResult> => {
  const requestPayload: TrainingRoundSubmitRequest = {
    session_id: requireString(params.sessionId, 'sessionId'),
    scenario_id: requireString(params.scenarioId, 'scenarioId'),
    user_input: requireString(params.userInput, 'userInput'),
  };

  const selectedOption = normalizeOptionalString(params.selectedOption);
  if (selectedOption) {
    requestPayload.selected_option = selectedOption;
  }

  const mediaTasks = normalizeTrainingRoundSubmitMediaTasks(params.mediaTasks);
  if (mediaTasks && mediaTasks.length > 0) {
    requestPayload.media_tasks = mediaTasks;
  }

  try {
    const response = await httpClient.post('/v1/training/round/submit', requestPayload, {
      timeout: 90000,
    });
    const result = normalizeTrainingRoundSubmitPayload(
      unwrapApiData<TrainingRoundSubmitResponse>(response)
    );

    assertSessionId(result.sessionId, 'training round submit');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to submit training round.',
      'Training round submission timed out.'
    );
  }
};

export const createTrainingMediaTask = async (
  params: TrainingMediaTaskCreateParams
): Promise<TrainingMediaTaskResult> => {
  const requestPayload: TrainingMediaTaskCreateRequest = {
    session_id: requireString(params.sessionId, 'sessionId'),
    task_type: normalizeTrainingMediaTaskType(params.taskType),
    payload: normalizeTrainingMediaTaskPayloadObject(params.payload),
    max_retries: normalizeTrainingMediaTaskMaxRetries(params.maxRetries),
  };

  const roundNo = normalizeTrainingMediaTaskRoundNo(params.roundNo);
  if (roundNo !== undefined) {
    requestPayload.round_no = roundNo;
  }

  const idempotencyKey = normalizeOptionalString(params.idempotencyKey);
  if (idempotencyKey) {
    requestPayload.idempotency_key = idempotencyKey;
  }

  try {
    const response = await httpClient.post('/v1/training/media/tasks', requestPayload, {
      timeout: 60000,
    });
    const result = normalizeTrainingMediaTaskPayload(
      unwrapApiData<TrainingMediaTaskApiResponse>(response)
    );

    if (!result) {
      throw new ServiceError({
        code: 'INVALID_RESPONSE',
        message: 'Missing task payload in training media create response.',
      });
    }

    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to create training media task.',
      'Training media task creation timed out.'
    );
  }
};

export const getTrainingMediaTask = async (taskId: string): Promise<TrainingMediaTaskResult> => {
  const normalizedTaskId = requireString(taskId, 'taskId');

  try {
    const response = await httpClient.get(`/v1/training/media/tasks/${normalizedTaskId}`, {
      timeout: 30000,
    });
    const result = normalizeTrainingMediaTaskPayload(
      unwrapApiData<TrainingMediaTaskApiResponse>(response)
    );

    if (!result) {
      throw new ServiceError({
        code: 'INVALID_RESPONSE',
        message: 'Missing task payload in training media get response.',
      });
    }

    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to load training media task.',
      'Training media task query timed out.'
    );
  }
};

export const listTrainingMediaTasks = async (
  params: TrainingMediaTaskListParams
): Promise<TrainingMediaTaskListResult> => {
  const normalizedSessionId = requireString(params.sessionId, 'sessionId');
  const roundNo = normalizeTrainingMediaTaskRoundNo(params.roundNo);

  try {
    const response = await httpClient.get(
      `/v1/training/media/sessions/${normalizedSessionId}/tasks`,
      {
        timeout: 30000,
        params: roundNo !== undefined ? { round_no: roundNo } : undefined,
      }
    );
    const result = normalizeTrainingMediaTaskListPayload(
      unwrapApiData<TrainingMediaTaskListResponse>(response)
    );

    assertSessionId(result.sessionId, 'training media task list');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to list training media tasks.',
      'Training media task list timed out.'
    );
  }
};

export const getTrainingProgress = async (
  sessionId: string
): Promise<TrainingProgressResult> => {
  const normalizedSessionId = requireString(sessionId, 'sessionId');

  try {
    const response = await httpClient.get(`/v1/training/progress/${normalizedSessionId}`, {
      timeout: 30000,
    });
    const result = normalizeTrainingProgressPayload(
      unwrapApiData<TrainingProgressResponse>(response)
    );

    assertSessionId(result.sessionId, 'training progress');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to load training progress.',
      'Training progress request timed out.'
    );
  }
};

export const getTrainingSessionSummary = async (
  sessionId: string
): Promise<TrainingSessionSummaryResult> => {
  const normalizedSessionId = requireString(sessionId, 'sessionId');

  try {
    const response = await httpClient.get(`/v1/training/sessions/${normalizedSessionId}`, {
      timeout: 30000,
    });
    const result = normalizeTrainingSessionSummaryPayload(
      unwrapApiData<TrainingSessionSummaryResponse>(response)
    );

    assertSessionId(result.sessionId, 'training session summary');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to restore training session.',
      'Training session restore timed out.'
    );
  }
};

export const getTrainingReport = async (
  sessionId: string
): Promise<TrainingReportResult> => {
  const normalizedSessionId = requireString(sessionId, 'sessionId');

  try {
    const response = await httpClient.get(`/v1/training/report/${normalizedSessionId}`, {
      timeout: 30000,
    });
    const result = normalizeTrainingReportPayload(
      unwrapApiData<TrainingReportResponse>(response)
    );

    assertSessionId(result.sessionId, 'training report');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to load training report.',
      'Training report request timed out.'
    );
  }
};

export const getTrainingDiagnostics = async (
  sessionId: string
): Promise<TrainingDiagnosticsResult> => {
  const normalizedSessionId = requireString(sessionId, 'sessionId');

  try {
    const response = await httpClient.get(`/v1/training/diagnostics/${normalizedSessionId}`, {
      timeout: 30000,
    });
    const result = normalizeTrainingDiagnosticsPayload(
      unwrapApiData<TrainingDiagnosticsResponse>(response)
    );

    assertSessionId(result.sessionId, 'training diagnostics');
    return result;
  } catch (error: unknown) {
    throw toTrainingServiceError(
      error,
      'Failed to load training diagnostics.',
      'Training diagnostics request timed out.'
    );
  }
};
