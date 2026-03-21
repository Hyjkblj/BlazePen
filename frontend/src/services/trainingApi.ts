import httpClient, { getErrorData, getErrorStatus, unwrapApiData } from '@/services/httpClient';
import type { ServiceErrorCode } from '@/services/serviceError';
import { ServiceError, toServiceError } from '@/services/serviceError';
import type {
  ApiErrorData,
  TrainingDiagnosticsResponse,
  TrainingInitRequest,
  TrainingInitResponse,
  TrainingProgressResponse,
  TrainingReportResponse,
  TrainingRoundSubmitRequest,
  TrainingRoundSubmitResponse,
  TrainingScenarioNextRequest,
  TrainingScenarioNextResponse,
  TrainingSessionSummaryResponse,
} from '@/types/api';
import type {
  TrainingDiagnosticsResult,
  TrainingInitResult,
  TrainingProgressResult,
  TrainingReportResult,
  TrainingSessionSummaryResult,
  TrainingRoundSubmitParams,
  TrainingRoundSubmitResult,
  TrainingScenarioNextParams,
  TrainingScenarioNextResult,
  TrainingSessionInitParams,
} from '@/types/training';
import {
  normalizeTrainingDiagnosticsPayload,
  normalizeTrainingInitPayload,
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
    return new ServiceError({
      code: mappedErrorCode,
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
