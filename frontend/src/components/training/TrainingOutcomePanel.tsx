import { Card, Descriptions, Empty, List, Typography } from 'antd';
import type {
  TrainingConsequenceEvent,
  TrainingEvaluation,
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

function TrainingOutcomePanel({ latestOutcome }: TrainingOutcomePanelProps) {
  return (
    <Card className="training-shell__panel training-shell__panel--antd" bordered={false}>
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
              <List
                size="small"
                className="training-shell__metric-list training-shell__metric-list--antd"
                dataSource={
                  latestOutcome.evaluation.evidence.length > 0
                    ? latestOutcome.evaluation.evidence
                    : ['No evidence returned.']
                }
                renderItem={(item) => <List.Item>{item}</List.Item>}
              />
            </div>

            <div>
              <Typography.Title level={5}>Consequence Events</Typography.Title>
              <List
                size="small"
                className="training-shell__metric-list training-shell__metric-list--antd"
                dataSource={
                  latestOutcome.consequenceEvents.length > 0
                    ? latestOutcome.consequenceEvents.map(
                        (item) => `${item.label || item.eventType}: ${item.summary || 'no summary'}`
                      )
                    : ['No consequence events in this round.']
                }
                renderItem={(item) => <List.Item>{item}</List.Item>}
              />
            </div>

            <div>
              <Typography.Title level={5}>Decision Context</Typography.Title>
              <List
                size="small"
                className="training-shell__metric-list training-shell__metric-list--antd"
                dataSource={buildDecisionSummaryRows(latestOutcome.decisionContext)}
                renderItem={(item) => <List.Item>{item}</List.Item>}
              />
            </div>
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
