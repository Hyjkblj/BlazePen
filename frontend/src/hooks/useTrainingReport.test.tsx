// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TrainingFlowProvider } from '@/contexts';
import type { TrainingReportResult } from '@/types/training';
import { useTrainingReport } from './useTrainingReport';

const trainingApiMocks = vi.hoisted(() => ({
  getTrainingReport: vi.fn(),
}));

vi.mock('@/services/trainingApi', () => trainingApiMocks);

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;

  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });

  return { promise, resolve, reject };
}

function Wrapper({ children }: { children: ReactNode }) {
  return <TrainingFlowProvider>{children}</TrainingFlowProvider>;
}

describe('useTrainingReport', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it('ignores a stale report response when the explicit sessionId changes', async () => {
    const firstRequest = createDeferred<TrainingReportResult>();
    const secondRequest = createDeferred<TrainingReportResult>();

    trainingApiMocks.getTrainingReport
      .mockReturnValueOnce(firstRequest.promise)
      .mockReturnValueOnce(secondRequest.promise);

    const { result, rerender } = renderHook(
      ({ sessionId }) => useTrainingReport(sessionId),
      {
        initialProps: { sessionId: 'session-old' },
        wrapper: Wrapper,
      }
    );

    rerender({ sessionId: 'session-new' });

    firstRequest.resolve({
      sessionId: 'session-old',
      characterId: null,
      status: 'completed',
      rounds: 1,
      kStateFinal: {},
      sStateFinal: {},
      improvement: 0.1,
      playerProfile: null,
      runtimeState: null,
      ending: null,
      summary: null,
      abilityRadar: [],
      stateRadar: [],
      growthCurve: [],
      history: [],
    });

    secondRequest.resolve({
      sessionId: 'session-new',
      characterId: null,
      status: 'completed',
      rounds: 2,
      kStateFinal: {},
      sStateFinal: {},
      improvement: 0.3,
      playerProfile: null,
      runtimeState: null,
      ending: null,
      summary: null,
      abilityRadar: [],
      stateRadar: [],
      growthCurve: [],
      history: [],
    });

    await waitFor(() => {
      expect(result.current.status).toBe('ready');
    });

    expect(result.current.data?.sessionId).toBe('session-new');
    expect(trainingApiMocks.getTrainingReport).toHaveBeenNthCalledWith(1, 'session-old');
    expect(trainingApiMocks.getTrainingReport).toHaveBeenNthCalledWith(2, 'session-new');
  });
});
