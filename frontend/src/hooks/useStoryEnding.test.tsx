// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { checkEnding } from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import { useStoryEnding } from './useStoryEnding';

vi.mock('@/services/gameApi', () => ({
  checkEnding: vi.fn(),
}));

const createDeferred = <T,>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });

  return {
    promise,
    resolve,
    reject,
  };
};

describe('useStoryEnding', () => {
  beforeEach(() => {
    vi.mocked(checkEnding).mockReset();
  });

  it('auto-loads and opens the ending dialog when a finished story session is present', async () => {
    vi.mocked(checkEnding).mockResolvedValueOnce({
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm ending.',
        favorability: 90,
        trust: 70,
        hostility: 10,
      },
    });

    const { result } = renderHook(() =>
      useStoryEnding({
        threadId: 'thread-finished',
        isGameFinished: true,
      })
    );

    await waitFor(() => {
      expect(result.current.endingStatus).toBe('ready');
      expect(result.current.isEndingDialogOpen).toBe(true);
      expect(result.current.endingSummary?.type).toBe('good_ending');
    });
  });

  it('allows retrying after the ending summary request fails', async () => {
    vi.mocked(checkEnding)
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'Ending unavailable.',
        })
      )
      .mockResolvedValueOnce({
        hasEnding: true,
        ending: {
          type: 'neutral_ending',
          description: 'A steady ending.',
          favorability: 55,
          trust: 58,
          hostility: 20,
        },
      });

    const { result } = renderHook(() =>
      useStoryEnding({
        threadId: 'thread-finished',
        isGameFinished: true,
      })
    );

    await waitFor(() => {
      expect(result.current.endingStatus).toBe('error');
      expect(result.current.endingError).toBe('Ending unavailable.');
    });

    await act(async () => {
      result.current.retryEndingSummary();
    });

    await waitFor(() => {
      expect(result.current.endingStatus).toBe('ready');
      expect(result.current.endingSummary?.type).toBe('neutral_ending');
    });
  });

  it('ignores a delayed ending result from the previous thread after the thread switches', async () => {
    const firstRequest = createDeferred<{
      hasEnding: boolean;
      ending: {
        type: string;
        description: string;
        favorability: number;
        trust: number;
        hostility: number;
      } | null;
    }>();
    const secondRequest = createDeferred<{
      hasEnding: boolean;
      ending: {
        type: string;
        description: string;
        favorability: number;
        trust: number;
        hostility: number;
      } | null;
    }>();

    vi.mocked(checkEnding)
      .mockImplementationOnce(() => firstRequest.promise)
      .mockImplementationOnce(() => secondRequest.promise);

    const { result, rerender } = renderHook(
      ({ threadId, isGameFinished }: { threadId: string | null; isGameFinished: boolean }) =>
        useStoryEnding({ threadId, isGameFinished }),
      {
        initialProps: {
          threadId: 'thread-old',
          isGameFinished: true,
        },
      }
    );

    await waitFor(() => {
      expect(checkEnding).toHaveBeenCalledWith('thread-old');
    });

    rerender({
      threadId: 'thread-new',
      isGameFinished: true,
    });

    await waitFor(() => {
      expect(checkEnding).toHaveBeenCalledWith('thread-new');
    });

    await act(async () => {
      secondRequest.resolve({
        hasEnding: true,
        ending: {
          type: 'neutral_ending',
          description: 'New thread ending.',
          favorability: 50,
          trust: 45,
          hostility: 18,
        },
      });
      await secondRequest.promise;
    });

    await waitFor(() => {
      expect(result.current.endingSummary?.description).toBe('New thread ending.');
      expect(result.current.endingStatus).toBe('ready');
    });

    await act(async () => {
      firstRequest.resolve({
        hasEnding: true,
        ending: {
          type: 'bad_ending',
          description: 'Old thread ending.',
          favorability: 10,
          trust: 8,
          hostility: 80,
        },
      });
      await firstRequest.promise;
    });

    expect(result.current.endingSummary?.description).toBe('New thread ending.');
    expect(result.current.endingSummary?.type).toBe('neutral_ending');
  });
});
