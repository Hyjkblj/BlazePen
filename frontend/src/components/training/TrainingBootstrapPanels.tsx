import { Button, Card, Descriptions, Form, Input, Radio, Space, Typography } from 'antd';
import type { TrainingMode } from '@/types/training';

interface TrainingFormDraftValue {
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
}

interface TrainingBootstrapPanelsProps {
  trainingMode: TrainingMode;
  setTrainingMode: (mode: TrainingMode) => void;
  formDraft: TrainingFormDraftValue;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
  canStartTraining: boolean;
  startTraining: () => void;
  hasResumeTarget: boolean;
  resumeSessionId: string | null;
  resumeTrainingMode: TrainingMode | null;
  resumeStatus: string | null;
  retryRestore: () => void;
}

const TRAINING_MODE_OPTIONS = [
  ['guided', '引导训练', '适合首次进入，优先给出推荐路径。'],
  ['self-paced', '自主训练', '保留更多手动选择空间。'],
  ['adaptive', '自适应训练', '按当前状态动态调整训练分支。'],
] as const;

function TrainingBootstrapPanels({
  trainingMode,
  setTrainingMode,
  formDraft,
  updateFormDraft,
  canStartTraining,
  startTraining,
  hasResumeTarget,
  resumeSessionId,
  resumeTrainingMode,
  resumeStatus,
  retryRestore,
}: TrainingBootstrapPanelsProps) {
  return (
    <div className="training-shell__workspace">
      <Card className="training-shell__panel training-shell__panel--primary training-shell__panel--antd">
        <Typography.Title level={4}>开始训练</Typography.Title>
        <Typography.Paragraph className="training-shell__empty">
          本地缓存只记住可恢复的 <code>sessionId</code> 入口，不保存服务端会话事实。页面刷新后统一走
          <code>session summary</code> 手动恢复。
        </Typography.Paragraph>

        <Radio.Group
          className="training-shell__mode-list training-shell__mode-list--antd"
          value={trainingMode}
          onChange={(event) => {
            setTrainingMode(event.target.value as TrainingMode);
          }}
        >
          <Space orientation="vertical" size={10} style={{ width: '100%' }}>
            {TRAINING_MODE_OPTIONS.map(([modeValue, title, description]) => (
              <Radio key={modeValue} className="training-shell__mode-radio" value={modeValue}>
                <span className="training-shell__mode-radio-title">{title}</span>
                <small className="training-shell__mode-radio-desc">{description}</small>
              </Radio>
            ))}
          </Space>
        </Radio.Group>

        <Form layout="vertical" className="training-shell__form-grid training-shell__form-grid--antd">
          <Form.Item label="characterId">
            <Input
              value={formDraft.characterId}
              onChange={(event) => updateFormDraft('characterId', event.target.value)}
              placeholder="可选，绑定训练角色"
              inputMode="numeric"
            />
          </Form.Item>
          <Form.Item label="姓名">
            <Input
              value={formDraft.playerName}
              onChange={(event) => updateFormDraft('playerName', event.target.value)}
              placeholder="可选"
            />
          </Form.Item>
          <Form.Item label="身份">
            <Input
              value={formDraft.playerIdentity}
              onChange={(event) => updateFormDraft('playerIdentity', event.target.value)}
              placeholder="例如：战地记者"
            />
          </Form.Item>
          <Form.Item label="性别">
            <Input
              value={formDraft.playerGender}
              onChange={(event) => updateFormDraft('playerGender', event.target.value)}
              placeholder="可选"
            />
          </Form.Item>
          <Form.Item label="年龄">
            <Input
              value={formDraft.playerAge}
              onChange={(event) => updateFormDraft('playerAge', event.target.value)}
              placeholder="可选"
              inputMode="numeric"
            />
          </Form.Item>
        </Form>

        <Button
          className="training-shell__primary-button"
          type="primary"
          disabled={!canStartTraining}
          onClick={startTraining}
        >
          启动训练
        </Button>
      </Card>

      <Card className="training-shell__panel training-shell__panel--antd">
        <Typography.Title level={4}>恢复入口</Typography.Title>
        {hasResumeTarget ? (
          <Descriptions className="training-shell__summary training-shell__summary--antd" column={1} size="small">
            <Descriptions.Item label="sessionId">{resumeSessionId ?? '当前上下文会话'}</Descriptions.Item>
            <Descriptions.Item label="训练模式">{resumeTrainingMode ?? '等待服务端恢复确认'}</Descriptions.Item>
            <Descriptions.Item label="缓存状态">{resumeStatus ?? '未知'}</Descriptions.Item>
          </Descriptions>
        ) : (
          <Typography.Paragraph className="training-shell__empty">
            当前没有可恢复的训练入口。首次进入会走初始化路径，刷新后才走服务端恢复路径。
          </Typography.Paragraph>
        )}

        <Space className="training-shell__stack-actions">
          <Button
            className="training-shell__secondary-button"
            disabled={!hasResumeTarget}
            onClick={retryRestore}
          >
            恢复上次训练
          </Button>
        </Space>
      </Card>
    </div>
  );
}

export default TrainingBootstrapPanels;
