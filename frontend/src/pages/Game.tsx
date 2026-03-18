import { Spin, Typography } from 'antd';
import SceneTransition from '@/components/SceneTransition';
import { GameDialogue, GameSceneBackground } from '@/components/Game';
import { useGameSessionFlow } from '@/flows/useGameSessionFlow';
import './Game.css';

const { Text } = Typography;

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
            <Spin size="large" />
            <div style={{ marginTop: '16px' }}>
              <Text>思考中...</Text>
            </div>
          </div>
        </div>
      )}

      <div className="game-scene-background">
        <GameSceneBackground
          shouldUseComposite={shouldUseComposite}
          compositeImageUrl={compositeImageUrl}
          sceneImageUrl={sceneImageUrl}
          characterImageUrl={characterImageUrl}
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
