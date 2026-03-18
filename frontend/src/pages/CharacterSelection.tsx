import type { KeyboardEvent } from 'react';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import StaticAssetImage from '@/components/StaticAssetImage';
import LoadingScreen from '@/components/loading';
import { useCharacterSelectionFlow } from '@/flows/useCharacterSelectionFlow';
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

  const handleImageSelect = (characterId: string, imageIndex = 0) => {
    if (loading) {
      return;
    }

    selectImage(characterId, imageIndex);
  };

  const handleCardKeyDown = (
    event: KeyboardEvent<HTMLDivElement>,
    characterId: string,
    imageIndex = 0
  ) => {
    if (loading) {
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectImage(characterId, imageIndex);
    }
  };

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
                <StaticAssetImage
                  key={`voice-character-${selectedImageUrlForVoice ?? 'empty'}`}
                  imageUrl={selectedImageUrlForVoice}
                  alt="角色预览"
                  imageClassName="voice-character-image"
                  placeholderClassName="voice-character-placeholder"
                  placeholder={<span className="placeholder-text">人物</span>}
                />
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
                    if (voices.length === 0) {
                      return null;
                    }

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
                              <button
                                type="button"
                                className="voice-selection-card-main"
                                onClick={() => selectVoice(voice.id)}
                                aria-pressed={selectedVoiceId === voice.id}
                              >
                                <span className="voice-selection-card-name">{voice.name}</span>
                                {voice.description && (
                                  <span className="voice-selection-card-desc">
                                    {voice.description}
                                  </span>
                                )}
                              </button>
                              <button
                                type="button"
                                className={`voice-preview-btn ${
                                  previewingVoiceId === voice.id ? 'is-loading' : ''
                                }`}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  void previewVoice(voice);
                                }}
                                disabled={previewingVoiceId !== null}
                                aria-busy={previewingVoiceId === voice.id}
                              >
                                {previewingVoiceId === voice.id ? '播放中...' : '试听'}
                              </button>
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
            <button type="button" className="voice-back-button" onClick={backToImageStep}>
              返回
            </button>
            <button
              type="button"
              className="voice-confirm-button"
              onClick={() => void confirmVoice()}
              disabled={loading}
            >
              确认
            </button>
          </div>
        </div>
      ) : (
        <div className="character-selection-content">
          <h2 className="selection-title">选择角色</h2>

          {hasGallery && primaryCharacter ? (
            <div className="character-options-grid">
              {primaryCharacter.imageUrls?.map((imageUrl, index) => (
                <div
                  key={`${primaryCharacter.id}-${index}`}
                  className={`character-option-card ${
                    selectedCharacter === primaryCharacter.id && selectedImageIndex === index
                      ? 'selected'
                      : ''
                  }`}
                  onClick={() => handleImageSelect(primaryCharacter.id, index)}
                  onKeyDown={(event) => handleCardKeyDown(event, primaryCharacter.id, index)}
                  role="button"
                  tabIndex={loading ? -1 : 0}
                  aria-pressed={
                    selectedCharacter === primaryCharacter.id && selectedImageIndex === index
                  }
                  aria-disabled={loading}
                >
                  <div className="character-image-container">
                    <StaticAssetImage
                      key={`${primaryCharacter.id}-${imageUrl ?? 'empty'}-${index}`}
                      imageUrl={imageUrl}
                      alt={`${primaryCharacter.name} - 选项 ${index + 1}`}
                      imageClassName="character-image"
                      placeholderClassName="character-image-placeholder"
                      placeholder={<span className="placeholder-text">人物</span>}
                    />
                  </div>

                  <span className="character-choice-button" aria-hidden="true">
                    CHOICE
                  </span>
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
                  onClick={() => handleImageSelect(character.id)}
                  onKeyDown={(event) => handleCardKeyDown(event, character.id)}
                  role="button"
                  tabIndex={loading ? -1 : 0}
                  aria-pressed={selectedCharacter === character.id}
                  aria-disabled={loading}
                >
                  <div className="character-image-container">
                    <StaticAssetImage
                      key={`${character.id}-${character.imageUrl ?? 'empty'}`}
                      imageUrl={character.imageUrl}
                      alt={character.name}
                      imageClassName="character-image"
                      placeholderClassName="character-image-placeholder"
                      placeholder={<span className="placeholder-text">人物</span>}
                    />
                  </div>

                  <span className="character-choice-button" aria-hidden="true">
                    CHOICE
                  </span>
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
