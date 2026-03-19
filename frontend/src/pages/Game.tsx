import SceneTransition from '@/components/SceneTransition';
import { GameDialogue, GameSceneBackground } from '@/components/Game';
import { useGameSessionFlow } from '@/flows/useGameSessionFlow';
import './Game.css';

function Game() {
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
    handleCharacterAssetError,
    handleCompositeAssetError,
    handleSceneAssetError,
    selectOption,
  } = useGameSessionFlow();

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
            <p className="game-loading-text">Loading...</p>
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
          onCompositeError={handleCompositeAssetError}
          onSceneError={handleSceneAssetError}
          onCharacterError={handleCharacterAssetError}
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
