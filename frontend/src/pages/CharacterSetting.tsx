import { Button, Input, Modal, Slider } from 'antd';
import {
  CloseOutlined,
  LeftOutlined,
  ManOutlined,
  ReloadOutlined,
  RightOutlined,
  WomanOutlined,
} from '@ant-design/icons';
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
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      <div className="character-setting-content">
        <div className="character-name-section">
          <div className="character-name-input">
            <span className="name-label">姓名:</span>
            <Input
              className="name-input"
              placeholder="请输入角色姓名"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={20}
              suffix={
                <Button
                  type="text"
                  icon={<ReloadOutlined />}
                  onClick={randomizeName}
                  className="name-random-icon"
                  size="small"
                />
              }
            />
          </div>

          <Button className="random-button" onClick={randomizeAll}>
            随机一组
          </Button>
        </div>

        <div className="character-setting-top">
          <div className="slider-group">
            <span className="slider-label">身高</span>
            <Slider
              min={140}
              max={200}
              value={height}
              onChange={(value) => setHeight(Array.isArray(value) ? value[0] : value)}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}cm` }}
            />
            <div className="slider-value">{height}cm</div>
          </div>

          <div className="slider-group">
            <span className="slider-label">体重</span>
            <Slider
              min={35}
              max={100}
              value={weight}
              onChange={(value) => setWeight(Array.isArray(value) ? value[0] : value)}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}kg` }}
            />
            <div className="slider-value">{weight}kg</div>
          </div>

          <div className="slider-group">
            <span className="slider-label">年龄</span>
            <Slider
              min={16}
              max={60}
              value={age}
              onChange={(value) => setAge(Array.isArray(value) ? value[0] : value)}
              style={{ flex: 1, minWidth: 120 }}
              tooltip={{ formatter: (value) => `${value}岁` }}
            />
            <div className="slider-value">{age}岁</div>
          </div>

          <Button
            className="gender-button"
            onClick={toggleGender}
            icon={gender === 'male' ? <ManOutlined /> : <WomanOutlined />}
          >
            性别: {gender === 'male' ? '男' : '女'}
          </Button>
        </div>

        <div className="character-setting-middle">
          <div className="character-options">
            {characterCategories.map((category, index) => (
              <Button
                key={category}
                className={`option-button ${currentCategory === index ? 'active' : ''}`}
                onClick={() => setCurrentCategory(index)}
              >
                {category}
              </Button>
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
                      <div
                        key={option}
                        className={`option-item ${selectedStyle === index ? 'selected' : ''}`}
                        onClick={() => setSelectedStyle(index)}
                      >
                        <span className="option-number">{index + 1}.</span>
                        <span className="option-text">{option}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="category-navigation">
          <Button className="nav-arrow-button" icon={<LeftOutlined />} onClick={previousCategory} />
          <Button className="nav-arrow-button" icon={<RightOutlined />} onClick={nextCategory} />
          <Button className="confirm-button" onClick={openConfirmModal}>
            confirm
          </Button>
        </div>
      </div>

      <Modal
        title="确认角色信息"
        open={isModalVisible}
        onCancel={closeConfirmModal}
        footer={[
          <Button key="cancel" onClick={closeConfirmModal}>
            取消
          </Button>,
          <Button key="confirm" type="primary" onClick={() => void submit()}>
            确认创建
          </Button>,
        ]}
        width={620}
        className="character-confirm-modal"
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
                      <Button
                        type="text"
                        icon={<CloseOutlined />}
                        onClick={keyword.onRemove}
                        className="keyword-tag-remove"
                        size="small"
                      />
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
                      <Button
                        type="text"
                        icon={<CloseOutlined />}
                        onClick={keyword.onRemove}
                        className="keyword-tag-remove"
                        size="small"
                      />
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
                    <Button
                      type="text"
                      icon={<CloseOutlined />}
                      onClick={selectedStyleChip.onRemove}
                      className="keyword-tag-remove"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default CharacterSetting;
