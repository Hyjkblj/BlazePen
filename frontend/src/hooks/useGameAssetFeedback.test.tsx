// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { useGameAssetFeedback } from './useGameAssetFeedback';

const createFeedbackSpy = (): FeedbackContextValue => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  dismiss: vi.fn(),
});

const createActionSpies = () => ({
  markCompositeAssetFailed: vi.fn(),
  markSceneAssetFailed: vi.fn(),
  markCharacterAssetFailed: vi.fn(),
});

describe('useGameAssetFeedback', () => {
  it('deduplicates repeated warnings for the same failed asset resource', () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();

    const { result } = renderHook(() =>
      useGameAssetFeedback({
        feedback,
        actions,
        compositeImageUrl: '/broken-composite.png',
        sceneImageUrl: '/scene.png',
        characterImageUrl: '/character.png',
      })
    );

    act(() => {
      result.current.handleCompositeAssetError();
      result.current.handleCompositeAssetError();
    });

    expect(actions.markCompositeAssetFailed).toHaveBeenCalledTimes(2);
    expect(feedback.warning).toHaveBeenCalledTimes(1);
    expect(feedback.warning).toHaveBeenCalledWith(
      'Composite scene failed to load. Switched to the background fallback.'
    );
  });

  it('emits a new warning when the failing resource changes after a rerender', () => {
    const feedback = createFeedbackSpy();
    const actions = createActionSpies();

    const { result, rerender } = renderHook(
      ({
        compositeImageUrl,
      }: {
        compositeImageUrl: string | null;
      }) =>
        useGameAssetFeedback({
          feedback,
          actions,
          compositeImageUrl,
          sceneImageUrl: '/scene.png',
          characterImageUrl: '/character.png',
        }),
      {
        initialProps: {
          compositeImageUrl: '/broken-composite-v1.png',
        },
      }
    );

    act(() => {
      result.current.handleCompositeAssetError();
    });

    rerender({
      compositeImageUrl: '/broken-composite-v2.png',
    });

    act(() => {
      result.current.handleCompositeAssetError();
    });

    expect(feedback.warning).toHaveBeenCalledTimes(2);
  });
});
