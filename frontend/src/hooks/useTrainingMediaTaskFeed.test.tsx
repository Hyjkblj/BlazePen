// @vitest-environment jsdom

import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import { listTrainingMediaTasks } from '@/services/trainingApi';
import { useTrainingMediaTaskFeed } from './useTrainingMediaTaskFeed';

vi.mock('@/services/trainingApi', () => ({
  listTrainingMediaTasks: vi.fn(),
}));

const createTask = (overrides: Record<string, unknown> = {}) => ({
  taskId: 'task-1',
  sessionId: 'session-1',
  roundNo: 2,
  taskType: 'image',
  status: 'pending' as const,
  result: null,
  error: null,
  createdAt: '2026-03-25T12:00:00Z',
  updatedAt: '2026-03-25T12:00:00Z',
  startedAt: null,
  finishedAt: null,
  ...overrides,
});

describe('useTrainingMediaTaskFeed', () => {
  beforeEach(() => {
    vi.mocked(listTrainingMediaTasks).mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('passes roundNo to list API and filters out tasks from other rounds defensively', async () => {
    vi.mocked(listTrainingMediaTasks).mockResolvedValueOnce({
      sessionId: 'session-1',
      items: [createTask(), createTask({ taskId: 'task-old', roundNo: 1 })],
    });

    const { result } = renderHook(() =>
      useTrainingMediaTaskFeed({
        sessionId: 'session-1',
        roundNo: 2,
        pollIntervalMs: 1000,
      })
    );

    await waitFor(() => {
      expect(result.current.status).toBe('ready');
    });

    expect(listTrainingMediaTasks).toHaveBeenCalledWith({
      sessionId: 'session-1',
      roundNo: 2,
    });
    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0].taskId).toBe('task-1');
    expect(result.current.tasks[0].roundNo).toBe(2);
  });

  it('keeps previous ready state when silent polling refresh fails', async () => {
    vi.mocked(listTrainingMediaTasks)
      .mockResolvedValueOnce({
        sessionId: 'session-1',
        items: [createTask({ status: 'running' })],
      })
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'poll timeout',
        })
      );

    const { result } = renderHook(() =>
      useTrainingMediaTaskFeed({
        sessionId: 'session-1',
        roundNo: 2,
        pollIntervalMs: 1000,
      })
    );

    await waitFor(() => {
      expect(result.current.status).toBe('ready');
    });
    expect(result.current.isPolling).toBe(true);

    await waitFor(() => {
      expect(listTrainingMediaTasks).toHaveBeenCalledTimes(2);
    }, { timeout: 3000 });

    expect(result.current.status).toBe('ready');
    expect(result.current.errorMessage).toBeNull();
    expect(result.current.tasks[0].status).toBe('running');
  });
});
