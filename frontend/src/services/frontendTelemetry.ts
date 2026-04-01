import { logger } from '@/utils/logger';
import { isServiceError } from './serviceError';

export type FrontendTelemetryDomain = 'app' | 'character' | 'story' | 'training';
export type FrontendTelemetryStatus = 'requested' | 'succeeded' | 'failed';
export type FrontendTelemetryEvent =
  | 'app.render'
  | 'character.create'
  | 'story.init'
  | 'story.turn.submit'
  | 'training.init'
  | 'training.restore'
  | 'training.form.hydration'
  | 'training.round.submit'
  | 'training.scene_image.create'
  | 'training.scene_image.poll'
  | 'training.scene_image.asset_error';

export interface FrontendTelemetryErrorContext {
  name?: string;
  message?: string;
  code?: string;
  status?: number;
  traceId?: string | null;
  retryable?: boolean;
}

export interface FrontendTelemetryPayload {
  type: 'frontend_telemetry';
  domain: FrontendTelemetryDomain;
  event: FrontendTelemetryEvent;
  status: FrontendTelemetryStatus;
  occurredAt: string;
  metadata?: Record<string, unknown>;
  error?: FrontendTelemetryErrorContext;
}

export interface TrackFrontendTelemetryOptions {
  domain: FrontendTelemetryDomain;
  event: FrontendTelemetryEvent;
  status: FrontendTelemetryStatus;
  metadata?: Record<string, unknown>;
  cause?: unknown;
}

export const FRONTEND_TELEMETRY_EVENT_NAME = 'blazepen:frontend-telemetry';
const FRONTEND_TELEMETRY_GLOBAL_KEY = '__BLAZEPEN_FRONTEND_TELEMETRY__';
const FRONTEND_TELEMETRY_BUFFER_LIMIT = 200;
const telemetryEndpoint = import.meta.env.VITE_FRONTEND_TELEMETRY_ENDPOINT?.trim() ?? '';

type FrontendTelemetryHost = typeof globalThis & {
  [FRONTEND_TELEMETRY_GLOBAL_KEY]?: FrontendTelemetryPayload[];
};

const getTelemetryHost = (): FrontendTelemetryHost => globalThis as FrontendTelemetryHost;

const getTelemetryBuffer = (): FrontendTelemetryPayload[] => {
  const host = getTelemetryHost();
  if (Array.isArray(host[FRONTEND_TELEMETRY_GLOBAL_KEY])) {
    return host[FRONTEND_TELEMETRY_GLOBAL_KEY];
  }

  const buffer: FrontendTelemetryPayload[] = [];
  host[FRONTEND_TELEMETRY_GLOBAL_KEY] = buffer;
  return buffer;
};

const storeTelemetryPayload = (payload: FrontendTelemetryPayload) => {
  const buffer = getTelemetryBuffer();
  buffer.push(payload);

  if (buffer.length > FRONTEND_TELEMETRY_BUFFER_LIMIT) {
    buffer.splice(0, buffer.length - FRONTEND_TELEMETRY_BUFFER_LIMIT);
  }
};

const dispatchTelemetryPayload = (payload: FrontendTelemetryPayload) => {
  if (typeof window === 'undefined' || typeof window.dispatchEvent !== 'function') {
    return;
  }

  if (typeof CustomEvent !== 'function') {
    return;
  }

  window.dispatchEvent(
    new CustomEvent<FrontendTelemetryPayload>(FRONTEND_TELEMETRY_EVENT_NAME, {
      detail: payload,
    })
  );
};

const publishTelemetryPayload = (payload: FrontendTelemetryPayload) => {
  if (!telemetryEndpoint) {
    return;
  }

  const body = JSON.stringify(payload);

  try {
    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      const blob = new Blob([body], {
        type: 'application/json',
      });
      navigator.sendBeacon(telemetryEndpoint, blob);
      return;
    }
  } catch {
    // Keep the local store as the stable fallback sink when beacon transport fails.
  }

  if (typeof fetch !== 'function') {
    return;
  }

  void fetch(telemetryEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    keepalive: true,
  }).catch(() => undefined);
};

const toTelemetryErrorContext = (
  error: unknown
): FrontendTelemetryErrorContext | undefined => {
  if (isServiceError(error)) {
    return {
      name: error.name,
      message: error.message,
      code: error.code,
      status: error.status,
      traceId: error.traceId,
      retryable: error.retryable,
    };
  }

  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
    };
  }

  return undefined;
};

export const readFrontendTelemetryEvents = (): FrontendTelemetryPayload[] => [
  ...getTelemetryBuffer(),
];

export const clearFrontendTelemetryEvents = () => {
  getTelemetryBuffer().splice(0);
};

export const trackFrontendTelemetry = ({
  domain,
  event,
  status,
  metadata,
  cause,
}: TrackFrontendTelemetryOptions): FrontendTelemetryPayload => {
  const normalizedMetadata: Record<string, unknown> | undefined = (() => {
    const base = metadata ? { ...metadata } : undefined;
    const errorContext = cause ? toTelemetryErrorContext(cause) : undefined;
    if (!base || !errorContext) {
      return base;
    }
    if (base.traceId === undefined && errorContext.traceId !== undefined) {
      base.traceId = errorContext.traceId;
    }
    if (base.errorCode === undefined && errorContext.code) {
      base.errorCode = errorContext.code;
    }
    if (base.httpStatus === undefined && typeof errorContext.status === 'number') {
      base.httpStatus = errorContext.status;
    }
    return base;
  })();

  const payload: FrontendTelemetryPayload = {
    type: 'frontend_telemetry',
    domain,
    event,
    status,
    occurredAt: new Date().toISOString(),
    metadata: normalizedMetadata,
    error: cause ? toTelemetryErrorContext(cause) : undefined,
  };

  storeTelemetryPayload(payload);
  dispatchTelemetryPayload(payload);
  publishTelemetryPayload(payload);

  if (status === 'failed') {
    logger.error('[frontend-telemetry]', payload);
  } else {
    logger.debug('[frontend-telemetry]', payload);
  }

  return payload;
};
