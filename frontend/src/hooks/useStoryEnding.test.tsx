// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getStoryEndingSummary } from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import type { StoryEndingSummaryResult } from '@/types/game';
import { useStoryEnding } from './useStoryEnding';

vi.mock('@/services/gameApi', () => ({
  getStoryEndingSummary: vi.fn(),
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
    vi.mocked(getStoryEndingSummary).mockReset();
  });

  it('auto-loads and opens the ending dialog when a finished story session is present', async () => {
    vi.mocked(getStoryEndingSummary).mockResolvedValueOnce({
      threadId: 'thread-finished',
      status: 'completed',
      roundNo: 6,
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm ending.',
        sceneId: 'study_room',
        eventTitle: 'Final Promise',
        keyStates: {
          favorability: 90,
          trust: 70,
          hostility: 10,
          dependence: null,
        },
      },
      updatedAt: '2026-03-20T10:00:00Z',
      expiresAt: '2026-03-20T10:30:00Z',
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
    vi.mocked(getStoryEndingSummary)
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'Ending unavailable.',
        })
      )
      .mockResolvedValueOnce({
        threadId: 'thread-finished',
        status: 'completed',
        roundNo: 6,
        hasEnding: true,
        ending: {
          type: 'neutral_ending',
          description: 'A steady ending.',
          sceneId: 'cafe_nearby',
          eventTitle: 'Quiet Resolution',
          keyStates: {
            favorability: 55,
            trust: 58,
            hostility: 20,
            dependence: null,
          },
        },
        updatedAt: '2026-03-20T10:00:00Z',
        expiresAt: '2026-03-20T10:30:00Z',
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
    const firstRequest = createDeferred<StoryEndingSummaryResult>();
    const secondRequest = createDeferred<StoryEndingSummaryResult>();

    vi.mocked(getStoryEndingSummary)
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
      expect(getStoryEndingSummary).toHaveBeenCalledWith('thread-old');
    });

    rerender({
      threadId: 'thread-new',
      isGameFinished: true,
    });

    await waitFor(() => {
      expect(getStoryEndingSummary).toHaveBeenCalledWith('thread-new');
    });

    await act(async () => {
      secondRequest.resolve({
        threadId: 'thread-new',
        status: 'completed',
        roundNo: 7,
        hasEnding: true,
        ending: {
          type: 'neutral_ending',
          description: 'New thread ending.',
          sceneId: 'cafe_nearby',
          eventTitle: 'Second Chance',
          keyStates: {
            favorability: 50,
            trust: 45,
            hostility: 18,
            dependence: null,
          },
        },
        updatedAt: '2026-03-20T11:00:00Z',
        expiresAt: '2026-03-20T11:30:00Z',
      });
      await secondRequest.promise;
    });

    await waitFor(() => {
      expect(result.current.endingSummary?.description).toBe('New thread ending.');
      expect(result.current.endingStatus).toBe('ready');
    });

    await act(async () => {
      firstRequest.resolve({
        threadId: 'thread-old',
        status: 'completed',
        roundNo: 5,
        hasEnding: true,
        ending: {
          type: 'bad_ending',
          description: 'Old thread ending.',
          sceneId: 'study_room',
          eventTitle: 'Missed Moment',
          keyStates: {
            favorability: 10,
            trust: 8,
            hostility: 80,
            dependence: null,
          },
        },
        updatedAt: '2026-03-20T09:00:00Z',
        expiresAt: '2026-03-20T09:30:00Z',
      });
      await firstRequest.promise;
    });

    expect(result.current.endingSummary?.description).toBe('New thread ending.');
    expect(result.current.endingSummary?.type).toBe('neutral_ending');
  });
});
