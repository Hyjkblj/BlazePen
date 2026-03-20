// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import { readStoryResumeTarget } from '@/storage/storySessionCache';
import { useFirstStepFlow } from './useFirstStepFlow';

vi.mock('@/contexts', () => ({
  useFeedback: vi.fn(),
  useGameFlow: vi.fn(),
}));

vi.mock('@/storage/storySessionCache', () => ({
  readStoryResumeTarget: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

const createFeedbackSpy = () => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  dismiss: vi.fn(),
});

describe('useFirstStepFlow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockNavigate.mockReset();
    vi.mocked(readStoryResumeTarget).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('warns when no resumable story target is available', async () => {
    const feedback = createFeedbackSpy();
    const setRestoreSession = vi.fn();

    vi.mocked(useFeedback).mockReturnValue(feedback);
    vi.mocked(useGameFlow).mockReturnValue({
      setRestoreSession,
    } as never);
    vi.mocked(readStoryResumeTarget).mockReturnValue(null);

    const { result } = renderHook(() => useFirstStepFlow());

    await act(async () => {
      await result.current.continueGame();
    });

    expect(feedback.warning).toHaveBeenCalledWith('没有找到可继续的故事记录，请先开始新的故事。');
    expect(setRestoreSession).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('continues from the active story session without depending on the local resume save', async () => {
    const feedback = createFeedbackSpy();
    const setRestoreSession = vi.fn();

    vi.mocked(useFeedback).mockReturnValue(feedback);
    vi.mocked(useGameFlow).mockReturnValue({
      setRestoreSession,
    } as never);
    vi.mocked(readStoryResumeTarget).mockReturnValue({
      threadId: 'thread-active',
      characterId: 'character-1',
      source: 'active-session',
    });

    const { result } = renderHook(() => useFirstStepFlow());

    await act(async () => {
      const continuePromise = result.current.continueGame();
      await vi.advanceTimersByTimeAsync(500);
      await continuePromise;
    });

    expect(setRestoreSession).toHaveBeenCalledWith('thread-active', 'character-1');
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.GAME);
    expect(feedback.error).not.toHaveBeenCalled();
  });

  it('uses the durable resume save when no active session is available', async () => {
    const feedback = createFeedbackSpy();
    const setRestoreSession = vi.fn();

    vi.mocked(useFeedback).mockReturnValue(feedback);
    vi.mocked(useGameFlow).mockReturnValue({
      setRestoreSession,
    } as never);
    vi.mocked(readStoryResumeTarget).mockReturnValue({
      threadId: 'thread-saved',
      characterId: undefined,
      source: 'resume-save',
    });

    const { result } = renderHook(() => useFirstStepFlow());

    await act(async () => {
      const continuePromise = result.current.continueGame();
      await vi.advanceTimersByTimeAsync(500);
      await continuePromise;
    });

    expect(setRestoreSession).toHaveBeenCalledWith('thread-saved', null);
    expect(mockNavigate).toHaveBeenCalledWith(ROUTES.GAME);
  });
});
