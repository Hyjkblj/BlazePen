// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ServiceError } from './serviceError';
import {
  clearFrontendTelemetryEvents,
  FRONTEND_TELEMETRY_EVENT_NAME,
  readFrontendTelemetryEvents,
  trackFrontendTelemetry,
  type FrontendTelemetryPayload,
} from './frontendTelemetry';

const loggerSpies = vi.hoisted(() => ({
  debug: vi.fn(),
  error: vi.fn(),
}));

vi.mock('@/utils/logger', () => ({
  logger: loggerSpies,
}));

describe('frontendTelemetry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    clearFrontendTelemetryEvents();
  });

  it('stores and dispatches non-failure events through the stable telemetry sink', () => {
    const observedPayloads: FrontendTelemetryPayload[] = [];
    const handleTelemetryEvent = (event: Event) => {
      observedPayloads.push((event as CustomEvent<FrontendTelemetryPayload>).detail);
    };

    window.addEventListener(FRONTEND_TELEMETRY_EVENT_NAME, handleTelemetryEvent as EventListener);

    const payload = trackFrontendTelemetry({
      domain: 'story',
      event: 'story.turn.submit',
      status: 'requested',
      metadata: {
        threadId: 'thread-1',
        optionIndex: 2,
      },
    });

    window.removeEventListener(
      FRONTEND_TELEMETRY_EVENT_NAME,
      handleTelemetryEvent as EventListener
    );

    expect(payload).toMatchObject({
      type: 'frontend_telemetry',
      domain: 'story',
      event: 'story.turn.submit',
      status: 'requested',
      metadata: {
        threadId: 'thread-1',
        optionIndex: 2,
      },
    });
    expect(readFrontendTelemetryEvents()).toEqual([payload]);
    expect(observedPayloads).toEqual([payload]);
    expect(loggerSpies.debug).toHaveBeenCalledWith('[frontend-telemetry]', payload);
    expect(loggerSpies.error).not.toHaveBeenCalled();
  });

  it('stores failure payloads with service error details', () => {
    const payload = trackFrontendTelemetry({
      domain: 'training',
      event: 'training.round.submit',
      status: 'failed',
      metadata: {
        sessionId: 'session-1',
        failureStage: 'submit',
      },
      cause: new ServiceError({
        code: 'TRAINING_SESSION_NOT_FOUND',
        message: 'Training session missing.',
        status: 404,
        traceId: 'trace-404',
        retryable: false,
      }),
    });

    expect(payload).toMatchObject({
      type: 'frontend_telemetry',
      domain: 'training',
      event: 'training.round.submit',
      status: 'failed',
      metadata: {
        sessionId: 'session-1',
        failureStage: 'submit',
        traceId: 'trace-404',
        errorCode: 'TRAINING_SESSION_NOT_FOUND',
        httpStatus: 404,
      },
      error: {
        code: 'TRAINING_SESSION_NOT_FOUND',
        status: 404,
        traceId: 'trace-404',
        retryable: false,
      },
    });
    expect(readFrontendTelemetryEvents()).toEqual([payload]);
    expect(loggerSpies.error).toHaveBeenCalledWith('[frontend-telemetry]', payload);
    expect(loggerSpies.debug).not.toHaveBeenCalled();
  });
});

