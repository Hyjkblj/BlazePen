import { useRef } from 'react';
import SceneTransition from '@/components/SceneTransition';
import { GameDialogue, GameSceneBackground } from '@/components/Game';
import { useFeedback } from '@/contexts';
import { useGameSessionFlow } from '@/flows/useGameSessionFlow';
import './Game.css';

function Game() {
  const feedback = useFeedback();
  const lastAssetErrorRef = useRef<{
    composite: string | null;
    scene: string | null;
    character: string | null;
  }>({
    composite: null,
    scene: null,
    character: null,
  });

  const {
    actNumber,
    showTransition,
    transitionSceneName,
    loading,
    shouldUseComposite,
    compositeImageUrl,
    sceneImageUrl,
    characterImageUrl,
    currentDialogue,
    currentOptions,
    dismissTransition,
    selectOption,
  } = useGameSessionFlow();

  const notifyAssetError = (
    kind: 'composite' | 'scene' | 'character',
    resourceKey: string | null,
    message: string
  ) => {
    const nextKey = resourceKey ?? `${kind}:missing`;
    if (lastAssetErrorRef.current[kind] === nextKey) {
      return;
    }

    lastAssetErrorRef.current[kind] = nextKey;
    feedback.warning(message);
  };

  return (
    <div className="game-scene-container">
      {showTransition && (
        <SceneTransition
          sceneName={transitionSceneName}
          actNumber={actNumber}
          onComplete={dismissTransition}
        />
      )}

      {loading && (
        <div className="game-loading-overlay">
          <div className="game-loading-content">
            <div className="game-loading-spinner" aria-hidden="true" />
            <p className="game-loading-text">思考中...</p>
          </div>
        </div>
      )}

      <div className="game-scene-background">
        <GameSceneBackground
          loading={loading}
          shouldUseComposite={shouldUseComposite}
          compositeImageUrl={compositeImageUrl}
          sceneImageUrl={sceneImageUrl}
          characterImageUrl={characterImageUrl}
          onCompositeError={() => {
            notifyAssetError(
              'composite',
              compositeImageUrl,
              '合成场景加载失败，已切换为占位背景。建议稍后重试或重新进入当前场景。'
            );
          }}
          onSceneError={() => {
            notifyAssetError(
              'scene',
              sceneImageUrl,
              '场景背景加载失败，已显示占位背景。你可以继续游戏，也可以稍后重试。'
            );
          }}
          onCharacterError={() => {
            notifyAssetError(
              'character',
              characterImageUrl,
              '角色立绘加载失败，当前将隐藏角色图层并继续游戏。'
            );
          }}
        />
      </div>

      <GameDialogue
        currentDialogue={currentDialogue}
        currentOptions={currentOptions}
        loading={loading}
        onOptionSelect={(index) => {
          void selectOption(index);
        }}
      />
    </div>
  );
}

export default Game;
