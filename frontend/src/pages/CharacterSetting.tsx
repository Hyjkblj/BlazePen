import ModalDialog from '@/components/ModalDialog';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CloseIcon,
  FemaleIcon,
  MaleIcon,
  RefreshIcon,
} from '@/components/icons';
import backgroundImage from '@/assets/images/settingcharacterbackground.png';
import LoadingScreen from '@/components/loading';
import {
  appearanceOptions,
  characterCategories,
  personalityOptions,
  styleOptions,
} from '@/config/characterOptions';
import { useCharacterCreationFlow } from '@/flows/useCharacterCreationFlow';
import './CharacterSetting.css';

interface MetricSliderProps {
  label: string;
  min: number;
  max: number;
  value: number;
  unit: string;
  onChange: (value: number) => void;
}

function MetricSlider({ label, min, max, value, unit, onChange }: MetricSliderProps) {
  return (
    <div className="slider-group">
      <span className="slider-label">{label}</span>
      <div className="slider-track">
        <input
          className="character-range-input"
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          aria-label={label}
        />
      </div>
      <div className="slider-value">
        {value}
        {unit}
      </div>
    </div>
  );
}

function CharacterSetting() {
  const {
    loading,
    loadingMessage,
    isModalVisible,
    name,
    height,
    weight,
    age,
    gender,
    currentCategory,
    selectedAppearance,
    selectedPersonality,
    selectedStyle,
    setName,
    setHeight,
    setWeight,
    setAge,
    setCurrentCategory,
    setSelectedStyle,
    openConfirmModal,
    closeConfirmModal,
    toggleAppearance,
    togglePersonality,
    randomizeName,
    randomizeAll,
    toggleGender,
    previousCategory,
    nextCategory,
    submit,
    selectedAppearanceKeywords,
    selectedPersonalityKeywords,
    selectedStyleChip,
  } = useCharacterCreationFlow();

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <div className="character-setting-container">
      <div
        className="character-setting-background"
        style={{
          backgroundImage: `url(${backgroundImage})`,
        }}
      />

      <div className="character-setting-content">
        <div className="character-name-section">
          <div className="character-name-input">
            <label className="name-label" htmlFor="character-name-input">
              姓名:
            </label>
            <div className="name-input-wrapper">
              <input
                id="character-name-input"
                className="name-input-field"
                placeholder="请输入角色姓名"
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={20}
              />
              <button
                type="button"
                onClick={randomizeName}
                className="name-random-icon"
                aria-label="随机姓名"
              >
                <RefreshIcon />
              </button>
            </div>
          </div>

          <button type="button" className="random-button" onClick={randomizeAll}>
            随机一组
          </button>
        </div>

        <div className="character-setting-top">
          <MetricSlider label="身高" min={140} max={200} value={height} unit="cm" onChange={setHeight} />
          <MetricSlider label="体重" min={35} max={100} value={weight} unit="kg" onChange={setWeight} />
          <MetricSlider label="年龄" min={16} max={60} value={age} unit="岁" onChange={setAge} />

          <button
            type="button"
            className="gender-button"
            onClick={toggleGender}
            aria-pressed={gender === 'female'}
          >
            <span className="character-setting-button-icon" aria-hidden="true">
              {gender === 'male' ? <MaleIcon /> : <FemaleIcon />}
            </span>
            <span>性别: {gender === 'male' ? '男' : '女'}</span>
          </button>
        </div>

        <div className="character-setting-middle">
          <div className="character-options">
            {characterCategories.map((category, index) => (
              <button
                key={category}
                type="button"
                className={`option-button ${currentCategory === index ? 'active' : ''}`}
                onClick={() => setCurrentCategory(index)}
                aria-pressed={currentCategory === index}
              >
                {category}
              </button>
            ))}
          </div>

          <div className="character-preview">
            <div className="preview-content">
              {currentCategory === 0 && (
                <div className="category-content">
                  <div className="appearance-grid">
                    {appearanceOptions.map((option, index) => (
                      <button
                        key={option}
                        type="button"
                        className={`appearance-button ${
                          selectedAppearance.includes(index) ? 'selected' : ''
                        }`}
                        onClick={() => toggleAppearance(index)}
                        aria-pressed={selectedAppearance.includes(index)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {currentCategory === 1 && (
                <div className="category-content">
                  <div className="personality-grid">
                    {personalityOptions.map((option, index) => (
                      <button
                        key={option}
                        type="button"
                        className={`personality-button ${
                          selectedPersonality.includes(index) ? 'selected' : ''
                        }`}
                        onClick={() => togglePersonality(index)}
                        aria-pressed={selectedPersonality.includes(index)}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {currentCategory === 2 && (
                <div className="category-content">
                  <div className="options-list">
                    {styleOptions.map((option, index) => (
                      <button
                        key={option}
                        type="button"
                        className={`option-item ${selectedStyle === index ? 'selected' : ''}`}
                        onClick={() => setSelectedStyle(index)}
                        aria-pressed={selectedStyle === index}
                      >
                        <span className="option-number">{index + 1}.</span>
                        <span className="option-text">{option}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="category-navigation">
          <button
            type="button"
            className="nav-arrow-button"
            onClick={previousCategory}
            aria-label="上一分类"
          >
            <ChevronLeftIcon />
          </button>
          <button
            type="button"
            className="nav-arrow-button"
            onClick={nextCategory}
            aria-label="下一分类"
          >
            <ChevronRightIcon />
          </button>
          <button type="button" className="confirm-button" onClick={openConfirmModal}>
            确认
          </button>
        </div>
      </div>

      <ModalDialog
        open={isModalVisible}
        title="确认角色信息"
        onClose={closeConfirmModal}
        width={620}
        className="character-confirm-modal"
        footer={
          <div className="character-confirm-footer">
            <button
              type="button"
              className="character-confirm-action"
              onClick={closeConfirmModal}
            >
              取消
            </button>
            <button
              type="button"
              className="character-confirm-action character-confirm-action-primary"
              onClick={() => void submit()}
            >
              确认创建
            </button>
          </div>
        }
      >
        <div className="modal-content">
          <div className="modal-section">
            <h4 className="modal-section-title">基本信息</h4>
            <div className="modal-info-item">
              <span className="info-label">姓名:</span>
              <span className="info-value">{name || '未填写'}</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">身高:</span>
              <span className="info-value">{height}cm</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">体重:</span>
              <span className="info-value">{weight}kg</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">年龄:</span>
              <span className="info-value">{age}岁</span>
            </div>
            <div className="modal-info-item">
              <span className="info-label">性别:</span>
              <span className="info-value">{gender === 'male' ? '男' : '女'}</span>
            </div>
          </div>

          <div className="modal-section">
            <h4 className="modal-section-title">已选关键词</h4>

            <div className="keywords-group">
              <div className="keywords-group-title">外貌</div>
              {selectedAppearanceKeywords.length > 0 ? (
                <div className="keywords-tags">
                  {selectedAppearanceKeywords.map((keyword) => (
                    <div key={keyword.value} className="keyword-tag-item">
                      <span className="keyword-tag-label">{keyword.label}</span>
                      <button
                        type="button"
                        onClick={keyword.onRemove}
                        className="keyword-tag-remove"
                        aria-label={`移除${keyword.label}`}
                      >
                        <CloseIcon />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-keywords-hint">暂未选择</div>
              )}
            </div>

            <div className="keywords-group">
              <div className="keywords-group-title">性格</div>
              {selectedPersonalityKeywords.length > 0 ? (
                <div className="keywords-tags">
                  {selectedPersonalityKeywords.map((keyword) => (
                    <div key={keyword.value} className="keyword-tag-item">
                      <span className="keyword-tag-label">{keyword.label}</span>
                      <button
                        type="button"
                        onClick={keyword.onRemove}
                        className="keyword-tag-remove"
                        aria-label={`移除${keyword.label}`}
                      >
                        <CloseIcon />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-keywords-hint">暂未选择</div>
              )}
            </div>

            {selectedStyleChip && (
              <div className="keywords-group">
                <div className="keywords-group-title">风格</div>
                <div className="keywords-tags">
                  <div className="keyword-tag-item">
                    <span className="keyword-tag-label">{selectedStyleChip.label}</span>
                    <button
                      type="button"
                      onClick={selectedStyleChip.onRemove}
                      className="keyword-tag-remove"
                      aria-label={`移除${selectedStyleChip.label}`}
                    >
                      <CloseIcon />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </ModalDialog>
    </div>
  );
}

export default CharacterSetting;
