import { Alert, Button, Card, Input, Radio, Space, Typography } from 'antd';
import type { TrainingIdentityPresetOption } from '@/services/trainingCharacterApi';

type TrainingFormDraftValue = {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
};

type TrainingIdentitySetupProps = {
  formDraft: TrainingFormDraftValue;
  hasGeneratedPortrait: boolean;
  isGeneratingPortrait: boolean;
  identityPresetError: string | null;
  identityPresetOptions: TrainingIdentityPresetOption[];
  identityPresetStatus: 'loading' | 'ready' | 'error';
  onGeneratePortrait: () => void;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
};

const HISTORIC_FEMALE_NAMES = [
  '王招娣',
  '李来娣',
  '张桂花',
  '赵春花',
  '孙小凤',
  '周秀兰',
  '吴玉梅',
  '郑彩云',
  '冯银花',
  '陈翠莲',
  '褚香兰',
  '卫秋菊',
  '蒋二妮',
  '沈素芬',
  '韩喜妹',
  '杨凤英',
  '朱兰英',
  '秦金莲',
  '尤巧云',
  '许桂芝',
  '何秀英',
  '吕春妮',
  '施玉兰',
  '孔淑芬',
  '曹翠花',
] as const;

const HISTORIC_MALE_NAMES = [
  '王大山',
  '李铁柱',
  '张有根',
  '赵满仓',
  '孙富贵',
  '周二喜',
  '吴长顺',
  '郑守业',
  '冯保国',
  '陈福生',
  '褚来旺',
  '卫成才',
  '蒋顺发',
  '沈德旺',
  '韩有福',
  '杨柱子',
  '朱进财',
  '秦老实',
  '尤庆余',
  '许旺财',
  '何金贵',
  '吕春生',
  '施忠厚',
  '孔天佑',
  '曹守田',
] as const;

const pickRandomName = (pool: readonly string[], currentName: string): string => {
  if (pool.length === 0) {
    return '';
  }

  const normalizedCurrentName = currentName.trim();
  const candidates =
    normalizedCurrentName === '' ? pool : pool.filter((item) => item !== normalizedCurrentName);
  const fallbackPool = candidates.length > 0 ? candidates : pool;
  const randomIndex = Math.floor(Math.random() * fallbackPool.length);
  return fallbackPool[randomIndex] ?? fallbackPool[0];
};

const normalizePresetGenderToLabel = (value: string): '男' | '女' => {
  const normalized = value.trim().toLowerCase();
  if (normalized === 'male' || normalized === 'm' || normalized === 'man' || normalized === '男') {
    return '男';
  }
  return '女';
};

function TrainingIdentitySetup({
  formDraft,
  hasGeneratedPortrait,
  isGeneratingPortrait,
  identityPresetError,
  identityPresetOptions,
  identityPresetStatus,
  onGeneratePortrait,
  updateFormDraft,
}: TrainingIdentitySetupProps) {
  const handleRandomName = () => {
    const gender = formDraft.playerGender === '男' ? '男' : '女';
    const selectedPool = gender === '男' ? HISTORIC_MALE_NAMES : HISTORIC_FEMALE_NAMES;
    const randomName = pickRandomName(selectedPool, formDraft.playerName);
    if (randomName) {
      updateFormDraft('playerName', randomName);
    }
  };

  const handleSelectPreset = (presetCode: string) => {
    const selectedPreset = identityPresetOptions.find((item) => item.code === presetCode);
    updateFormDraft('portraitPresetId', presetCode);
    if (!selectedPreset) {
      return;
    }

    updateFormDraft('playerIdentity', selectedPreset.identity);
    updateFormDraft('playerGender', normalizePresetGenderToLabel(selectedPreset.defaultGender));
    if (formDraft.playerName.trim() === '' && selectedPreset.defaultName) {
      updateFormDraft('playerName', selectedPreset.defaultName);
    }
  };

  return (
    <Card className="training-landing__setup-card">
      <Typography.Title className="training-landing__setup-title" level={4}>
        选择身份与基础信息
      </Typography.Title>

      <section className="training-landing__setup-section">
        <h3>身份预设</h3>
        {identityPresetStatus === 'loading' ? (
          <Typography.Text type="secondary">正在加载身份预设...</Typography.Text>
        ) : null}
        {identityPresetStatus === 'ready' ? (
          <Radio.Group
            className="training-landing__identity-group"
            value={formDraft.portraitPresetId}
            onChange={(event) => handleSelectPreset(String(event.target.value ?? ''))}
          >
            <Space orientation="vertical" size={8}>
              {identityPresetOptions.map((item) => (
                <Radio key={item.code} value={item.code}>
                  <div className="training-landing__identity-option">
                    <strong>{item.title}</strong>
                    <span>{item.description}</span>
                  </div>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        ) : null}
        {identityPresetError ? (
          <Alert
            className="training-landing__identity-alert"
            type="error"
            showIcon
            title={identityPresetError}
          />
        ) : null}
      </section>

      <section className="training-landing__setup-section">
        <div className="training-landing__meta-grid">
          <div className="training-landing__name-random">
            <Input
              value={formDraft.playerName}
              placeholder="姓名"
              onChange={(event) => updateFormDraft('playerName', event.target.value)}
            />
            <Button className="training-landing__name-random-btn" onClick={handleRandomName}>
              随机姓名
            </Button>
          </div>

          <div className="training-landing__gender-toggle">
            <Radio.Group
              className="training-landing__gender-switch"
              value={formDraft.playerGender === '男' ? '男' : '女'}
              onChange={(event) => updateFormDraft('playerGender', event.target.value)}
              optionType="button"
              buttonStyle="solid"
            >
              <Radio.Button value="女">女</Radio.Button>
              <Radio.Button value="男">男</Radio.Button>
            </Radio.Group>
          </div>

          <Input
            value={formDraft.playerAge}
            inputMode="numeric"
            placeholder="年龄"
            onChange={(event) => updateFormDraft('playerAge', event.target.value)}
          />
        </div>
      </section>

      <div className="training-landing__setup-actions">
        <Button
          className="training-landing__preview-generate"
          type="primary"
          loading={isGeneratingPortrait}
          disabled={isGeneratingPortrait || identityPresetStatus !== 'ready'}
          onClick={onGeneratePortrait}
        >
          {hasGeneratedPortrait ? '重新渲染' : '生成形象图'}
        </Button>
      </div>
    </Card>
  );
}

export default TrainingIdentitySetup;
