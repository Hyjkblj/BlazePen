import SceneTransition from '@/components/SceneTransition';
import {
  GameDialogue,
  GameSceneBackground,
  StoryEndingDialog,
  StorySessionToolbar,
  StorySessionTranscriptDialog,
} from '@/components/Game';
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
    optionsDisabledReason,
    hasTranscript,
    transcriptEntries,
    isTranscriptDialogOpen,
    canViewEnding,
    isEndingDialogOpen,
    endingStatus,
    endingSummary,
    endingError,
    dismissTransition,
    handleCharacterAssetError,
    handleCompositeAssetError,
    handleSceneAssetError,
    openTranscriptDialog,
    closeTranscriptDialog,
    openEndingDialog,
    closeEndingDialog,
    retryEndingSummary,
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

      <StorySessionToolbar
        hasTranscript={hasTranscript}
        canViewEnding={canViewEnding}
        endingStatus={endingStatus}
        onOpenTranscript={openTranscriptDialog}
        onOpenEnding={openEndingDialog}
      />

      <GameDialogue
        currentDialogue={currentDialogue}
        currentOptions={currentOptions}
        loading={loading}
        optionsDisabledReason={optionsDisabledReason}
        onOptionSelect={(index) => {
          void selectOption(index);
        }}
      />

      <StorySessionTranscriptDialog
        open={isTranscriptDialogOpen}
        entries={transcriptEntries}
        onClose={closeTranscriptDialog}
      />

      <StoryEndingDialog
        open={isEndingDialogOpen}
        endingStatus={endingStatus}
        endingSummary={endingSummary}
        endingError={endingError}
        onClose={closeEndingDialog}
        onRetry={retryEndingSummary}
      />
    </div>
  );
}

export default Game;
