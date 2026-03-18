import backgroundImage from '@/assets/images/firstbackground.jpg';
import StaticAssetImage from '@/components/StaticAssetImage';
import { ChevronLeftIcon, ChevronRightIcon } from '@/components/icons';
import LoadingScreen from '@/components/loading';
import { useFirstMeetingFlow } from '@/flows/useFirstMeetingFlow';
import './FirstMeetingSelection.css';

function FirstMeetingSelection() {
  const {
    loading,
    loadingMessage,
    sceneOptions,
    currentSceneIndex,
    currentScene,
    goToCharacterSetup,
    previousScene,
    nextScene,
    handleWheel,
    selectScene,
  } = useFirstMeetingFlow();

  if (loading && sceneOptions.length === 0) {
    return <LoadingScreen message={loadingMessage} />;
  }

  if (sceneOptions.length === 0) {
    return (
      <div className="first-meeting-selection-container">
        <div className="first-meeting-content">
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p>No scenes available.</p>
            <button type="button" className="scene-choice-button" onClick={goToCharacterSetup}>
              Back To Character Setup
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="first-meeting-selection-container">
      <div
        className="first-meeting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
        }}
      />

      <div className="first-meeting-content">
        <div className="meeting-title-banner">
          <span className="title-text">First Meeting</span>
        </div>

        <div className="scene-display-area" onWheel={handleWheel}>
          <button
            type="button"
            className="scene-nav-arrow scene-nav-left"
            onClick={previousScene}
            aria-label="Previous scene"
          >
            <ChevronLeftIcon />
          </button>

          <div className="scene-content">
            <StaticAssetImage
              key={`scene-img-${currentScene?.id ?? 'unknown'}-${currentSceneIndex}`}
              imageUrl={currentScene?.imageUrl}
              alt={currentScene?.name ?? 'Scene preview'}
              imageClassName="scene-image"
              placeholderClassName="scene-placeholder"
              placeholder={
                <>
                  <span className="placeholder-text">{currentScene?.name || 'Unknown'}</span>
                  {currentScene?.description && (
                    <span className="placeholder-description">{currentScene.description}</span>
                  )}
                </>
              }
            />
          </div>

          <button
            type="button"
            className="scene-nav-arrow scene-nav-right"
            onClick={nextScene}
            aria-label="Next scene"
          >
            <ChevronRightIcon />
          </button>
        </div>

        <div className="scene-choice-button-container">
          <button
            type="button"
            className="scene-choice-button"
            onClick={() => void selectScene()}
            disabled={loading}
          >
            Choose
          </button>
        </div>
      </div>
    </div>
  );
}

export default FirstMeetingSelection;
