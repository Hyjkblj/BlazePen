import SceneTransition from '@/components/SceneTransition';
import {
  GameDialogue,
  GameSceneBackground,
  StoryEndingDialog,
  StorySessionHistoryDialog,
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
    canViewHistory,
    isHistoryDialogOpen,
    historyStatus,
    historyError,
    historySession,
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
    openHistoryDialog,
    closeHistoryDialog,
    openEndingDialog,
    closeEndingDialog,
    retryHistoryLoad,
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
        canViewHistory={canViewHistory}
        canViewEnding={canViewEnding}
        historyStatus={historyStatus}
        endingStatus={endingStatus}
        onOpenTranscript={openTranscriptDialog}
        onOpenHistory={openHistoryDialog}
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

      <StorySessionHistoryDialog
        open={isHistoryDialogOpen}
        historyStatus={historyStatus}
        historySession={historySession}
        historyError={historyError}
        onClose={closeHistoryDialog}
        onRetry={retryHistoryLoad}
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
