// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getStorySessionHistory } from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import type { StorySessionHistoryResult } from '@/types/game';
import { useStorySessionHistory } from './useStorySessionHistory';

vi.mock('@/services/gameApi', () => ({
  getStorySessionHistory: vi.fn(),
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

describe('useStorySessionHistory', () => {
  beforeEach(() => {
    vi.mocked(getStorySessionHistory).mockReset();
  });

  it('loads persisted server history on demand', async () => {
    vi.mocked(getStorySessionHistory).mockResolvedValueOnce({
      threadId: 'thread-live',
      status: 'in_progress',
      currentRoundNo: 2,
      latestSceneId: 'study_room',
      updatedAt: '2026-03-20T12:00:00Z',
      expiresAt: '2026-03-20T12:30:00Z',
      history: [
        {
          roundNo: 1,
          status: 'in_progress',
          sceneId: 'study_room',
          eventTitle: 'First Meeting',
          characterDialogue: 'Nice to meet you.',
          userAction: {
            kind: 'option',
            summary: 'Wave back',
            rawInput: null,
            optionIndex: 0,
            optionText: 'Wave back',
            optionType: 'action',
          },
          stateSummary: {
            changes: {
              trust: 10,
            },
            currentStates: {
              trust: 60,
            },
          },
          isEventFinished: false,
          isGameFinished: false,
          createdAt: '2026-03-20T11:58:00Z',
        },
      ],
    });

    const { result } = renderHook(() =>
      useStorySessionHistory({
        threadId: 'thread-live',
      })
    );

    await act(async () => {
      result.current.openHistoryDialog();
    });

    await waitFor(() => {
      expect(result.current.historyStatus).toBe('ready');
      expect(result.current.isHistoryDialogOpen).toBe(true);
      expect(result.current.historySession?.history[0]?.eventTitle).toBe('First Meeting');
    });
  });

  it('allows retrying after the server history request fails', async () => {
    vi.mocked(getStorySessionHistory)
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'History unavailable.',
        })
      )
      .mockResolvedValueOnce({
        threadId: 'thread-live',
        status: 'in_progress',
        currentRoundNo: 2,
        latestSceneId: 'study_room',
        updatedAt: '2026-03-20T12:00:00Z',
        expiresAt: '2026-03-20T12:30:00Z',
        history: [],
      });

    const { result } = renderHook(() =>
      useStorySessionHistory({
        threadId: 'thread-live',
      })
    );

    await act(async () => {
      result.current.openHistoryDialog();
    });

    await waitFor(() => {
      expect(result.current.historyStatus).toBe('error');
      expect(result.current.historyError).toBe('History unavailable.');
    });

    await act(async () => {
      result.current.retryHistoryLoad();
    });

    await waitFor(() => {
      expect(result.current.historyStatus).toBe('empty');
    });
  });

  it('ignores a delayed history result from the previous thread after the thread switches', async () => {
    const firstRequest = createDeferred<StorySessionHistoryResult>();
    const secondRequest = createDeferred<StorySessionHistoryResult>();

    vi.mocked(getStorySessionHistory)
      .mockImplementationOnce(() => firstRequest.promise)
      .mockImplementationOnce(() => secondRequest.promise);

    const { result, rerender } = renderHook(
      ({ threadId }: { threadId: string | null }) =>
        useStorySessionHistory({
          threadId,
        }),
      {
        initialProps: {
          threadId: 'thread-old',
        },
      }
    );

    await act(async () => {
      result.current.openHistoryDialog();
    });

    await waitFor(() => {
      expect(getStorySessionHistory).toHaveBeenCalledWith('thread-old');
    });

    rerender({
      threadId: 'thread-new',
    });

    await act(async () => {
      result.current.openHistoryDialog();
    });

    await waitFor(() => {
      expect(getStorySessionHistory).toHaveBeenCalledWith('thread-new');
    });

    await act(async () => {
      secondRequest.resolve({
        threadId: 'thread-new',
        status: 'in_progress',
        currentRoundNo: 2,
        latestSceneId: 'cafe_nearby',
        updatedAt: '2026-03-20T13:00:00Z',
        expiresAt: '2026-03-20T13:30:00Z',
        history: [],
      });
      await secondRequest.promise;
    });

    await waitFor(() => {
      expect(result.current.historySession?.threadId).toBe('thread-new');
      expect(result.current.historyStatus).toBe('empty');
    });

    await act(async () => {
      firstRequest.resolve({
        threadId: 'thread-old',
        status: 'in_progress',
        currentRoundNo: 1,
        latestSceneId: 'study_room',
        updatedAt: '2026-03-20T12:00:00Z',
        expiresAt: '2026-03-20T12:30:00Z',
        history: [],
      });
      await firstRequest.promise;
    });

    expect(result.current.historySession?.threadId).toBe('thread-new');
  });
});
