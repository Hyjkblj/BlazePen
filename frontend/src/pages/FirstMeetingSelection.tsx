import { Button } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackground.jpg';
import LoadingScreen from '@/components/loading';
import { useFirstMeetingFlow } from '@/flows/useFirstMeetingFlow';
import { getStaticAssetUrl } from '@/services/assetUrl';
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
            <Button onClick={goToCharacterSetup}>Back To Character Setup</Button>
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
            className="scene-nav-arrow scene-nav-left"
            onClick={previousScene}
            aria-label="Previous scene"
          >
            <LeftOutlined />
          </button>

          <div className="scene-content">
            {currentScene?.imageUrl ? (
              <img
                key={`scene-img-${currentScene.id}-${currentSceneIndex}`}
                src={getStaticAssetUrl(currentScene.imageUrl)}
                alt={currentScene.name}
                className="scene-image"
                style={{ display: 'none' }}
                onLoad={(event) => {
                  const image = event.target as HTMLImageElement;
                  image.style.display = 'block';
                  const placeholder = image.parentElement?.querySelector(
                    '.scene-placeholder'
                  ) as HTMLElement | null;
                  if (placeholder) {
                    placeholder.style.display = 'none';
                  }
                }}
                onError={(event) => {
                  const target = event.target as HTMLImageElement;
                  target.style.display = 'none';
                  const placeholder = target.parentElement?.querySelector(
                    '.scene-placeholder'
                  ) as HTMLElement | null;
                  if (placeholder) {
                    placeholder.style.display = 'flex';
                  }
                }}
              />
            ) : null}

            <div
              className="scene-placeholder"
              style={{
                display: currentScene?.imageUrl ? 'none' : 'flex',
              }}
            >
              <span className="placeholder-text">{currentScene?.name || 'Unknown'}</span>
              {currentScene?.description && (
                <span className="placeholder-description">{currentScene.description}</span>
              )}
            </div>
          </div>

          <button
            className="scene-nav-arrow scene-nav-right"
            onClick={nextScene}
            aria-label="Next scene"
          >
            <RightOutlined />
          </button>
        </div>

        <div className="scene-choice-button-container">
          <Button className="scene-choice-button" onClick={() => void selectScene()} disabled={loading}>
            Choose
          </Button>
        </div>
      </div>
    </div>
  );
}

export default FirstMeetingSelection;
