import { getErrorData, getErrorMessage, getErrorStatus, isTimeoutError } from '@/services/httpClient';

export type ServiceErrorCode =
  | 'REQUEST_TIMEOUT'
  | 'VALIDATION_ERROR'
  | 'NOT_FOUND'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'SERVICE_UNAVAILABLE'
  | 'SESSION_EXPIRED'
  | 'INVALID_RESPONSE'
  | 'UNKNOWN_ERROR';

export interface ServiceErrorOptions {
  code: ServiceErrorCode;
  message: string;
  status?: number;
  details?: unknown;
  traceId?: string | null;
  retryable?: boolean;
  cause?: unknown;
}

export interface NormalizeServiceErrorOptions {
  fallbackMessage: string;
  fallbackCode?: ServiceErrorCode;
  overrideCode?: ServiceErrorCode;
  timeoutMessage?: string;
}

const readTraceId = (value: unknown): string | null => {
  if (!value || typeof value !== 'object') {
    return null;
  }

  const record = value as Record<string, unknown>;
  const traceId = record.traceId ?? record.trace_id;
  return typeof traceId === 'string' && traceId.trim() !== '' ? traceId.trim() : null;
};

const isRetryableStatus = (status?: number) => status === 408 || status === 429 || status === 503;

const mapStatusToCode = (status?: number): ServiceErrorCode | undefined => {
  switch (status) {
    case 400:
    case 422:
      return 'VALIDATION_ERROR';
    case 401:
      return 'UNAUTHORIZED';
    case 403:
      return 'FORBIDDEN';
    case 404:
      return 'NOT_FOUND';
    case 503:
      return 'SERVICE_UNAVAILABLE';
    default:
      return undefined;
  }
};

export class ServiceError extends Error {
  readonly code: ServiceErrorCode;
  readonly status?: number;
  readonly details?: unknown;
  readonly traceId?: string | null;
  readonly retryable: boolean;
  readonly cause?: unknown;

  constructor({
    code,
    message,
    status,
    details,
    traceId = null,
    retryable = false,
    cause,
  }: ServiceErrorOptions) {
    super(message);
    this.name = 'ServiceError';
    this.code = code;
    this.status = status;
    this.details = details;
    this.traceId = traceId;
    this.retryable = retryable;
    this.cause = cause;
  }
}

export const isServiceError = (error: unknown): error is ServiceError => error instanceof ServiceError;

export const getServiceErrorMessage = (error: unknown, fallbackMessage: string): string => {
  if (isServiceError(error)) {
    return error.message;
  }

  if (error instanceof Error && error.message.trim() !== '') {
    return error.message;
  }

  return fallbackMessage;
};

export const toServiceError = (
  error: unknown,
  {
    fallbackMessage,
    fallbackCode = 'UNKNOWN_ERROR',
    overrideCode,
    timeoutMessage = 'Request timed out. Please retry.',
  }: NormalizeServiceErrorOptions
): ServiceError => {
  if (isServiceError(error)) {
    return error;
  }

  if (isTimeoutError(error)) {
    return new ServiceError({
      code: overrideCode ?? 'REQUEST_TIMEOUT',
      message: timeoutMessage,
      status: getErrorStatus(error),
      details: getErrorData(error),
      traceId: readTraceId(getErrorData(error)),
      retryable: true,
      cause: error,
    });
  }

  const status = getErrorStatus(error);
  const errorData = getErrorData(error);
  const message = getErrorMessage(error) || fallbackMessage;

  return new ServiceError({
    code: overrideCode ?? mapStatusToCode(status) ?? fallbackCode,
    status,
    message: message.trim() !== '' ? message : fallbackMessage,
    details: errorData?.details ?? errorData?.detail ?? errorData?.error,
    traceId: readTraceId(errorData),
    retryable: isRetryableStatus(status),
    cause: error,
  });
};
