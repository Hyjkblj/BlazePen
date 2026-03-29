import { Card, Descriptions, Tag, Typography } from 'antd';
import type { TrainingRuntimeState } from '@/types/training';

interface TrainingSessionSummaryPanelProps {
  sessionId: string;
  trainingModeLabel: string | null;
  status: string;
  roundNo: number;
  totalRounds: number | null;
  progressLabel: string | null;
  characterId: string | null;
  currentSceneId: string | null;
  runtimeState: TrainingRuntimeState;
}

function TrainingSessionSummaryPanel({
  sessionId,
  trainingModeLabel,
  status,
  roundNo,
  totalRounds,
  progressLabel,
  characterId,
  currentSceneId,
  runtimeState,
}: TrainingSessionSummaryPanelProps) {
  const stateBarRows = [
    `editorTrust: ${runtimeState.stateBar.editorTrust}`,
    `publicStability: ${runtimeState.stateBar.publicStability}`,
    `sourceSafety: ${runtimeState.stateBar.sourceSafety}`,
  ];
  const runtimeFlagRows = [
    `panicTriggered: ${String(runtimeState.runtimeFlags.panicTriggered)}`,
    `sourceExposed: ${String(runtimeState.runtimeFlags.sourceExposed)}`,
    `editorLocked: ${String(runtimeState.runtimeFlags.editorLocked)}`,
    `highRiskPath: ${String(runtimeState.runtimeFlags.highRiskPath)}`,
  ];

  return (
    <Card className="training-shell__panel training-shell__panel--antd" variant="borderless">
      <Typography.Title level={4}>当前训练状态</Typography.Title>

      <Descriptions
        className="training-shell__summary training-shell__summary--antd"
        column={1}
        size="small"
      >
        <Descriptions.Item label="sessionId">{sessionId}</Descriptions.Item>
        <Descriptions.Item label="训练模式">{trainingModeLabel ?? '未指定'}</Descriptions.Item>
        <Descriptions.Item label="状态">
          <Tag color="processing">{status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="回合">
          {roundNo}
          {totalRounds !== null ? ` / ${totalRounds}` : ''}
        </Descriptions.Item>
        {progressLabel ? <Descriptions.Item label="进度">{progressLabel}</Descriptions.Item> : null}
        <Descriptions.Item label="characterId">{characterId ?? '未绑定'}</Descriptions.Item>
        <Descriptions.Item label="currentSceneId">{currentSceneId ?? '暂无'}</Descriptions.Item>
      </Descriptions>

      <div className="training-shell__state-grid">
        <div>
          <Typography.Title level={5}>State Bar</Typography.Title>
          <ul className="training-shell__metric-list training-shell__metric-list--antd">
            {stateBarRows.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <Typography.Title level={5}>Runtime Flags</Typography.Title>
          <ul className="training-shell__metric-list training-shell__metric-list--antd">
            {runtimeFlagRows.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}

export default TrainingSessionSummaryPanel;
