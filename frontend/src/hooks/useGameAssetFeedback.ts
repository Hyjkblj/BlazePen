import { useCallback, useRef } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import type { GameSessionActions } from './useGameState';

type AssetKind = 'composite' | 'scene' | 'character';

interface UseGameAssetFeedbackParams {
  feedback: FeedbackContextValue;
  actions: Pick<
    GameSessionActions,
    'markCompositeAssetFailed' | 'markSceneAssetFailed' | 'markCharacterAssetFailed'
  >;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
}

export interface UseGameAssetFeedbackResult {
  handleCompositeAssetError: () => void;
  handleSceneAssetError: () => void;
  handleCharacterAssetError: () => void;
}

export function useGameAssetFeedback({
  feedback,
  actions,
  compositeImageUrl,
  sceneImageUrl,
  characterImageUrl,
}: UseGameAssetFeedbackParams): UseGameAssetFeedbackResult {
  const lastAssetErrorRef = useRef<Record<AssetKind, string | null>>({
    composite: null,
    scene: null,
    character: null,
  });

  const notifyAssetError = useCallback(
    (kind: AssetKind, resourceKey: string | null, message: string) => {
      const nextKey = resourceKey ?? `${kind}:missing`;
      if (lastAssetErrorRef.current[kind] === nextKey) {
        return;
      }

      lastAssetErrorRef.current[kind] = nextKey;
      feedback.warning(message);
    },
    [feedback]
  );

  const handleCompositeAssetError = useCallback(() => {
    actions.markCompositeAssetFailed();
    notifyAssetError(
      'composite',
      compositeImageUrl,
      'Composite scene failed to load. Switched to the background fallback.'
    );
  }, [actions, compositeImageUrl, notifyAssetError]);

  const handleSceneAssetError = useCallback(() => {
    actions.markSceneAssetFailed();
    notifyAssetError(
      'scene',
      sceneImageUrl,
      'Scene background failed to load. A fallback background is shown instead.'
    );
  }, [actions, notifyAssetError, sceneImageUrl]);

  const handleCharacterAssetError = useCallback(() => {
    actions.markCharacterAssetFailed();
    notifyAssetError(
      'character',
      characterImageUrl,
      'Character portrait failed to load. The character layer is now hidden.'
    );
  }, [actions, characterImageUrl, notifyAssetError]);

  return {
    handleCompositeAssetError,
    handleSceneAssetError,
    handleCharacterAssetError,
  };
}
