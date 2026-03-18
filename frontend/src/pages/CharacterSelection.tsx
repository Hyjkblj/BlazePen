import { Button } from 'antd';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import { useCharacterSelectionFlow } from '@/flows/useCharacterSelectionFlow';
import { getStaticAssetUrl } from '@/services/assetUrl';
import './CharacterSelection.css';

function CharacterSelection() {
  const {
    loading,
    loadingMessage,
    characters,
    selectedCharacter,
    selectedImageIndex,
    step,
    presetVoices,
    selectedVoiceId,
    voicesLoading,
    previewingVoiceId,
    selectedImageUrlForVoice,
    selectImage,
    selectVoice,
    previewVoice,
    confirmVoice,
    backToImageStep,
  } = useCharacterSelectionFlow();

  if (loading && characters.length === 0) {
    return <LoadingScreen message={loadingMessage} />;
  }

  const primaryCharacter = characters[0];
  const hasGallery = Boolean(primaryCharacter?.imageUrls && primaryCharacter.imageUrls.length >= 3);

  return (
    <div className="character-selection-container">
      <div
        className="character-selection-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {step === 'voice' ? (
        <div className="character-selection-content voice-selection-layout">
          <h2 className="voice-selection-title">音色设定</h2>
          <p className="voice-selection-hint">
            选择角色的语音风格，游戏中的对话将使用该音色
          </p>

          <div className="voice-selection-panels">
            <div className="voice-selection-left">
              <div className="voice-character-panel">
                {selectedImageUrlForVoice ? (
                  <img
                    src={getStaticAssetUrl(selectedImageUrlForVoice)}
                    alt="人物"
                    className="voice-character-image"
                  />
                ) : (
                  <div className="voice-character-placeholder">
                    <span className="placeholder-text">人物</span>
                  </div>
                )}
              </div>

              {selectedVoiceId && (
                <div className="voice-current-selection">
                  <span className="voice-current-label">当前选择：</span>
                  <span className="voice-current-name">
                    {presetVoices.find((voice) => voice.id === selectedVoiceId)?.name ??
                      selectedVoiceId}
                  </span>
                </div>
              )}
            </div>

            <div className="voice-selection-right">
              {voicesLoading ? (
                <div className="voice-selection-loading">加载音色列表中...</div>
              ) : (
                <div className="voice-selection-grouped">
                  {[
                    { key: 'female', title: '女声' },
                    { key: 'male', title: '男声' },
                    { key: 'neutral', title: '中性' },
                  ].map(({ key, title }) => {
                    const voices = presetVoices.filter((voice) => (voice.gender || 'neutral') === key);
                    if (voices.length === 0) return null;

                    return (
                      <div key={key} className="voice-group">
                        <h3 className="voice-group-title">{title}</h3>
                        <div className="voice-selection-grid">
                          {voices.map((voice) => (
                            <div
                              key={voice.id}
                              className={`voice-selection-card ${
                                selectedVoiceId === voice.id ? 'selected' : ''
                              }`}
                            >
                              <Button
                                className="voice-selection-card-main"
                                onClick={() => selectVoice(voice.id)}
                              >
                                <span className="voice-selection-card-name">{voice.name}</span>
                                {voice.description && (
                                  <span className="voice-selection-card-desc">
                                    {voice.description}
                                  </span>
                                )}
                              </Button>
                              <Button
                                size="small"
                                className="voice-preview-btn"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  void previewVoice(voice);
                                }}
                                disabled={previewingVoiceId !== null}
                                loading={previewingVoiceId === voice.id}
                              >
                                {previewingVoiceId === voice.id ? '播放中...' : '试听'}
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div className="voice-selection-footer">
            <Button className="voice-back-button" onClick={backToImageStep}>
              返回
            </Button>
            <Button className="voice-confirm-button" onClick={() => void confirmVoice()} disabled={loading}>
              确认
            </Button>
          </div>
        </div>
      ) : (
        <div className="character-selection-content">
          <h2 className="selection-title">选择角色</h2>

          {hasGallery && primaryCharacter ? (
            <div className="character-options-grid">
              {primaryCharacter.imageUrls?.map((imageUrl, index) => (
                <div
                  key={index}
                  className={`character-option-card ${
                    selectedCharacter === primaryCharacter.id && selectedImageIndex === index
                      ? 'selected'
                      : ''
                  }`}
                  onClick={() => selectImage(primaryCharacter.id, index)}
                >
                  <div className="character-image-container">
                    {imageUrl ? (
                      <img
                        src={getStaticAssetUrl(imageUrl)}
                        alt={`${primaryCharacter.name} - 选项 ${index + 1}`}
                        className="character-image"
                        onError={(event) => {
                          const target = event.target as HTMLImageElement;
                          target.style.display = 'none';
                          const placeholder = target.parentElement?.querySelector(
                            '.character-image-placeholder'
                          ) as HTMLElement | null;
                          if (placeholder) {
                            placeholder.style.display = 'flex';
                          }
                        }}
                      />
                    ) : null}

                    <div
                      className="character-image-placeholder"
                      style={{ display: imageUrl ? 'none' : 'flex' }}
                    >
                      <span className="placeholder-text">人物</span>
                    </div>
                  </div>

                  <Button
                    className="character-choice-button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      selectImage(primaryCharacter.id, index);
                    }}
                    disabled={loading}
                  >
                    CHOICE
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="character-options-grid">
              {characters.map((character) => (
                <div
                  key={character.id}
                  className={`character-option-card ${
                    selectedCharacter === character.id ? 'selected' : ''
                  }`}
                >
                  <div className="character-image-container">
                    {character.imageUrl ? (
                      <img
                        src={getStaticAssetUrl(character.imageUrl)}
                        alt={character.name}
                        className="character-image"
                        onError={(event) => {
                          const target = event.target as HTMLImageElement;
                          target.style.display = 'none';
                          const placeholder = target.parentElement?.querySelector(
                            '.character-image-placeholder'
                          ) as HTMLElement | null;
                          if (placeholder) {
                            placeholder.style.display = 'flex';
                          }
                        }}
                      />
                    ) : null}

                    <div
                      className="character-image-placeholder"
                      style={{ display: character.imageUrl ? 'none' : 'flex' }}
                    >
                      <span className="placeholder-text">人物</span>
                    </div>
                  </div>

                  <Button
                    className="character-choice-button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      selectImage(character.id, 0);
                    }}
                    disabled={loading}
                  >
                    CHOICE
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {loading && characters.length > 0 && <LoadingScreen message={loadingMessage} />}
    </div>
  );
}

export default CharacterSelection;
