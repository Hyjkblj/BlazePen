import { Button, Card, Input, Radio, Space, Typography } from 'antd';

type TrainingFormDraftValue = {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
};

type TrainingIdentitySetupProps = {
  canStartTraining: boolean;
  formDraft: TrainingFormDraftValue;
  isStarting: boolean;
  onBack: () => void;
  onConfirm: () => void;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
};

const IDENTITY_OPTIONS = [
  '战地记者',
  '摄影记者',
  '通讯联络员',
  '前线记录员',
] as const;

const IMAGE_OPTIONS = [
  {
    value: 'correspondent-female',
    title: '女记者形象',
    description: '冷静、坚定，适合叙事主视觉。',
    gender: '女',
  },
  {
    value: 'correspondent-male',
    title: '男记者形象',
    description: '沉稳、克制，强调纪实视角。',
    gender: '男',
  },
  {
    value: 'frontline-photographer',
    title: '摄影记者形象',
    description: '突出镜头语言与现场张力。',
    gender: '',
  },
  {
    value: 'radio-operator',
    title: '通讯员形象',
    description: '强调联络与信息传递职责。',
    gender: '',
  },
] as const;

function TrainingIdentitySetup({
  canStartTraining,
  formDraft,
  isStarting,
  onBack,
  onConfirm,
  updateFormDraft,
}: TrainingIdentitySetupProps) {
  const canConfirm =
    canStartTraining &&
    formDraft.playerIdentity.trim() !== '' &&
    formDraft.portraitPresetId.trim() !== '';

  return (
    <Card className="training-landing__setup-card">
      <Typography.Title className="training-landing__setup-title" level={4}>
        选择身份与个人形象
      </Typography.Title>

      <Typography.Paragraph className="training-landing__setup-tip">
        先完成角色选择，再进入训练。该信息会作为本轮训练的人物档案写入会话。
      </Typography.Paragraph>

      <section className="training-landing__setup-section">
        <h3>身份</h3>
        <Radio.Group
          className="training-landing__identity-group"
          value={formDraft.playerIdentity}
          onChange={(event) => updateFormDraft('playerIdentity', event.target.value)}
        >
          <Space direction="vertical" size={8}>
            {IDENTITY_OPTIONS.map((item) => (
              <Radio key={item} value={item}>
                {item}
              </Radio>
            ))}
          </Space>
        </Radio.Group>
      </section>

      <section className="training-landing__setup-section">
        <h3>个人形象</h3>
        <div className="training-landing__image-grid">
          {IMAGE_OPTIONS.map((item) => {
            const isActive = formDraft.portraitPresetId === item.value;
            return (
              <button
                key={item.value}
                className={`training-landing__image-card${isActive ? ' training-landing__image-card--active' : ''}`}
                type="button"
                onClick={() => {
                  updateFormDraft('portraitPresetId', item.value);
                  if (!formDraft.playerGender.trim() && item.gender) {
                    updateFormDraft('playerGender', item.gender);
                  }
                }}
              >
                <strong>{item.title}</strong>
                <span>{item.description}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="training-landing__setup-section">
        <h3>补充信息</h3>
        <div className="training-landing__meta-grid">
          <Input
            value={formDraft.playerName}
            placeholder="姓名（可选）"
            onChange={(event) => updateFormDraft('playerName', event.target.value)}
          />
          <Input
            value={formDraft.playerGender}
            placeholder="性别（可选）"
            onChange={(event) => updateFormDraft('playerGender', event.target.value)}
          />
          <Input
            value={formDraft.playerAge}
            inputMode="numeric"
            placeholder="年龄（可选）"
            onChange={(event) => updateFormDraft('playerAge', event.target.value)}
          />
          <Input
            value={formDraft.characterId}
            inputMode="numeric"
            placeholder="角色ID（可选，数字）"
            onChange={(event) => updateFormDraft('characterId', event.target.value)}
          />
        </div>
      </section>

      <div className="training-landing__setup-actions">
        <Button className="training-landing__back" onClick={onBack}>
          返回
        </Button>
        <Button
          className="training-landing__confirm"
          type="primary"
          loading={isStarting}
          disabled={!canConfirm}
          onClick={onConfirm}
        >
          进入训练
        </Button>
      </div>
    </Card>
  );
}

export default TrainingIdentitySetup;
