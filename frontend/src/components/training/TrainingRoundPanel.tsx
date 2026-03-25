import { Button, Card, Input, Radio, Space, Typography } from 'antd';
import type { TrainingScenario } from '@/types/training';

const { TextArea } = Input;

interface TrainingRoundPanelProps {
  isCompleted: boolean;
  currentScenario: TrainingScenario | null;
  selectedOptionId: string | null;
  selectOption: (optionId: string) => void;
  responseInput: string;
  setResponseInput: (value: string) => void;
  submissionPreview: string | null;
  canSubmitRound: boolean;
  submitCurrentRound: () => void;
  retryRestore: () => void;
  clearWorkspace: () => void;
  completedEnding: Record<string, unknown> | null;
}

function TrainingRoundPanel({
  isCompleted,
  currentScenario,
  selectedOptionId,
  selectOption,
  responseInput,
  setResponseInput,
  submissionPreview,
  canSubmitRound,
  submitCurrentRound,
  retryRestore,
  clearWorkspace,
  completedEnding,
}: TrainingRoundPanelProps) {
  return (
    <Card className="training-shell__panel training-shell__panel--primary training-shell__panel--antd" bordered={false}>
      {isCompleted ? (
        <>
          <Typography.Title level={4}>训练完成</Typography.Title>
          <Typography.Paragraph className="training-shell__empty">
            当前训练已完成。完成态仍通过服务端 <code>session summary</code> 恢复，不回退到本地事实源。
          </Typography.Paragraph>
          {completedEnding ? (
            <pre className="training-shell__json-card">{JSON.stringify(completedEnding, null, 2)}</pre>
          ) : null}
          <Space className="training-shell__stack-actions">
            <Button className="training-shell__primary-button" type="primary" onClick={clearWorkspace}>
              开始新的训练
            </Button>
          </Space>
        </>
      ) : currentScenario ? (
        <>
          <Typography.Title level={4}>{currentScenario.title}</Typography.Title>
          <Typography.Paragraph className="training-shell__scenario-meta">
            {(currentScenario.eraDate || '未标注时间') + ' · ' + (currentScenario.location || '未标注地点')}
          </Typography.Paragraph>
          <Typography.Paragraph className="training-shell__scenario-brief">
            {currentScenario.brief || '当前场景暂无额外简介。'}
          </Typography.Paragraph>

          <div className="training-shell__scenario-grid">
            <div>
              <Typography.Title level={5}>Mission</Typography.Title>
              <Typography.Paragraph>
                {currentScenario.mission || '保持训练目标可推进。'}
              </Typography.Paragraph>
            </div>
            <div>
              <Typography.Title level={5}>Decision Focus</Typography.Title>
              <Typography.Paragraph>
                {currentScenario.decisionFocus || '根据现场状态完成判断。'}
              </Typography.Paragraph>
            </div>
          </div>

          {currentScenario.options.length > 0 ? (
            <Radio.Group
              className="training-shell__option-list training-shell__option-list--antd"
              value={selectedOptionId ?? undefined}
              onChange={(event) => selectOption(event.target.value)}
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {currentScenario.options.map((option) => (
                  <Radio key={option.id} className="training-shell__option-radio" value={option.id}>
                    <strong>{option.label}</strong>
                    <span>{option.impactHint || '无额外提示'}</span>
                  </Radio>
                ))}
              </Space>
            </Radio.Group>
          ) : null}

          <label className="training-shell__field training-shell__field--textarea">
            <span>本轮操作说明</span>
            <TextArea
              value={responseInput}
              onChange={(event) => setResponseInput(event.target.value)}
              placeholder="填写训练操作、采访策略或补充说明。若只选择选项，也会提交选项标签。"
              rows={6}
            />
          </label>

          {submissionPreview ? (
            <Typography.Paragraph className="training-shell__submission-preview">
              当前已选选项：{submissionPreview}
            </Typography.Paragraph>
          ) : null}

          <Space className="training-shell__stack-actions" wrap>
            <Button
              className="training-shell__primary-button"
              type="primary"
              disabled={!canSubmitRound}
              onClick={submitCurrentRound}
            >
              提交本轮训练
            </Button>
            <Button className="training-shell__secondary-button" onClick={retryRestore}>
              按服务端会话恢复
            </Button>
          </Space>
        </>
      ) : (
        <>
          <Typography.Title level={4}>训练恢复待确认</Typography.Title>
          <Typography.Paragraph className="training-shell__empty">
            当前训练会话没有可直接提交的场景。请按服务端 <code>session summary</code> 重建当前可继续状态。
          </Typography.Paragraph>
          <Space className="training-shell__stack-actions">
            <Button className="training-shell__primary-button" type="primary" onClick={retryRestore}>
              恢复当前训练
            </Button>
          </Space>
        </>
      )}
    </Card>
  );
}

export default TrainingRoundPanel;
