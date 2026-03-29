import { Button, Card, Descriptions, Empty, Space, Tag, Typography } from 'antd';
import type {
  TrainingConsequenceEvent,
  TrainingEvaluation,
  TrainingMediaTaskView,
  TrainingRoundDecisionContext,
} from '@/types/training';

interface TrainingOutcomeView {
  roundNo: number;
  evaluation: TrainingEvaluation;
  consequenceEvents: TrainingConsequenceEvent[];
  decisionContext: TrainingRoundDecisionContext | null;
}

interface TrainingOutcomePanelProps {
  latestOutcome: TrainingOutcomeView | null;
  mediaTasks: TrainingMediaTaskView[];
  mediaTaskFeedStatus: 'idle' | 'loading' | 'ready' | 'error';
  mediaTaskFeedErrorMessage: string | null;
  isPollingMediaTasks: boolean;
  refreshMediaTasks: () => void;
}

const buildDecisionSummaryRows = (
  decisionContext: TrainingRoundDecisionContext | null
): string[] => {
  if (!decisionContext) {
    return ['No decision context returned for this round.'];
  }

  const diverged =
    decisionContext.recommendedScenarioId !== null &&
    decisionContext.selectedScenarioId !== decisionContext.recommendedScenarioId;

  return [
    `selectionSource: ${decisionContext.selectionSource}`,
    `selectedScenarioId: ${decisionContext.selectedScenarioId}`,
    `recommendedScenarioId: ${decisionContext.recommendedScenarioId ?? 'none'}`,
    `candidatePool: ${decisionContext.candidatePool.length}`,
    `recommendationDiverged: ${String(diverged)}`,
  ];
};

const resolveMediaTaskStatusColor = (status: TrainingMediaTaskView['status']): string => {
  switch (status) {
    case 'succeeded':
      return 'green';
    case 'failed':
    case 'timeout':
      return 'red';
    case 'running':
      return 'blue';
    case 'pending':
      return 'gold';
    default:
      return 'default';
  }
};

function TrainingOutcomePanel({
  latestOutcome,
  mediaTasks,
  mediaTaskFeedStatus,
  mediaTaskFeedErrorMessage,
  isPollingMediaTasks,
  refreshMediaTasks,
}: TrainingOutcomePanelProps) {
  const evidenceRows =
    latestOutcome && latestOutcome.evaluation.evidence.length > 0
      ? latestOutcome.evaluation.evidence
      : ['No evidence returned.'];
  const consequenceRows =
    latestOutcome && latestOutcome.consequenceEvents.length > 0
      ? latestOutcome.consequenceEvents.map(
          (item) => `${item.label || item.eventType}: ${item.summary || 'no summary'}`
        )
      : ['No consequence events in this round.'];

  return (
    <Card className="training-shell__panel training-shell__panel--antd" variant="borderless">
      <Typography.Title level={4}>Latest Round Outcome</Typography.Title>
      {latestOutcome ? (
        <>
          <Descriptions
            className="training-shell__summary training-shell__summary--antd"
            column={1}
            size="small"
          >
            <Descriptions.Item label="roundNo">{latestOutcome.roundNo}</Descriptions.Item>
            <Descriptions.Item label="confidence">
              {latestOutcome.evaluation.confidence}
            </Descriptions.Item>
            <Descriptions.Item label="evalMode">
              {latestOutcome.evaluation.evalMode}
            </Descriptions.Item>
            <Descriptions.Item label="riskFlags">
              {latestOutcome.evaluation.riskFlags.join(', ') || 'none'}
            </Descriptions.Item>
            <Descriptions.Item label="selectionSource">
              {latestOutcome.decisionContext?.selectionSource ?? 'none'}
            </Descriptions.Item>
          </Descriptions>

          <div className="training-shell__state-grid">
            <div>
              <Typography.Title level={5}>Evidence</Typography.Title>
              <ul className="training-shell__metric-list training-shell__metric-list--antd">
                {evidenceRows.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>

            <div>
              <Typography.Title level={5}>Consequence Events</Typography.Title>
              <ul className="training-shell__metric-list training-shell__metric-list--antd">
                {consequenceRows.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>

            <div>
              <Typography.Title level={5}>Decision Context</Typography.Title>
              <ul className="training-shell__metric-list training-shell__metric-list--antd">
                {buildDecisionSummaryRows(latestOutcome.decisionContext).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="training-shell__media-task-panel">
            <Space className="training-shell__media-task-header" wrap>
              <Typography.Title level={5}>Media Tasks</Typography.Title>
              <Button size="small" onClick={refreshMediaTasks}>
                Refresh
              </Button>
              {isPollingMediaTasks ? <Typography.Text type="secondary">Polling...</Typography.Text> : null}
              {mediaTaskFeedStatus === 'loading' ? (
                <Typography.Text type="secondary">Loading...</Typography.Text>
              ) : null}
            </Space>

            {mediaTaskFeedErrorMessage ? (
              <Typography.Paragraph type="danger">{mediaTaskFeedErrorMessage}</Typography.Paragraph>
            ) : null}

            {mediaTasks.length === 0 ? (
              <Typography.Paragraph type="secondary">
                No media tasks in current training session.
              </Typography.Paragraph>
            ) : (
              <div className="training-shell__metric-list training-shell__metric-list--antd">
                {mediaTasks.map((item) => (
                  <div key={item.taskId} className="training-shell__media-task-item">
                    <Space wrap>
                      <Tag>{item.taskType}</Tag>
                      <Tag color={resolveMediaTaskStatusColor(item.status)}>{item.status}</Tag>
                      <Typography.Text code>{item.taskId}</Typography.Text>
                    </Space>
                    {item.errorMessage ? (
                      <Typography.Paragraph className="training-shell__media-task-detail" type="danger">
                        {item.errorMessage}
                      </Typography.Paragraph>
                    ) : item.previewUrl ? (
                      <Typography.Paragraph className="training-shell__media-task-detail">
                        <Typography.Link href={item.previewUrl} target="_blank" rel="noreferrer">
                          {item.previewUrl}
                        </Typography.Link>
                      </Typography.Paragraph>
                    ) : item.audioUrl ? (
                      <Typography.Paragraph className="training-shell__media-task-detail">
                        <Typography.Link href={item.audioUrl} target="_blank" rel="noreferrer">
                          {item.audioUrl}
                        </Typography.Link>
                      </Typography.Paragraph>
                    ) : item.generatedText ? (
                      <Typography.Paragraph className="training-shell__media-task-detail">
                        {item.generatedText}
                      </Typography.Paragraph>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="The latest submitted outcome will appear here."
        />
      )}
    </Card>
  );
}

export default TrainingOutcomePanel;
