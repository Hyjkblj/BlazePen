import { Card, Descriptions, List, Tag, Typography } from 'antd';
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
  return (
    <Card className="training-shell__panel training-shell__panel--antd" bordered={false}>
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
          <List
            size="small"
            className="training-shell__metric-list training-shell__metric-list--antd"
            dataSource={[
              `editorTrust: ${runtimeState.stateBar.editorTrust}`,
              `publicStability: ${runtimeState.stateBar.publicStability}`,
              `sourceSafety: ${runtimeState.stateBar.sourceSafety}`,
            ]}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </div>
        <div>
          <Typography.Title level={5}>Runtime Flags</Typography.Title>
          <List
            size="small"
            className="training-shell__metric-list training-shell__metric-list--antd"
            dataSource={[
              `panicTriggered: ${String(runtimeState.runtimeFlags.panicTriggered)}`,
              `sourceExposed: ${String(runtimeState.runtimeFlags.sourceExposed)}`,
              `editorLocked: ${String(runtimeState.runtimeFlags.editorLocked)}`,
              `highRiskPath: ${String(runtimeState.runtimeFlags.highRiskPath)}`,
            ]}
            renderItem={(item) => <List.Item>{item}</List.Item>}
          />
        </div>
      </div>
    </Card>
  );
}

export default TrainingSessionSummaryPanel;
