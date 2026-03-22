import type {
  TrainingConsequenceEvent,
  TrainingEvaluation,
} from '@/types/training';

interface TrainingOutcomeView {
  roundNo: number;
  evaluation: TrainingEvaluation;
  consequenceEvents: TrainingConsequenceEvent[];
}

interface TrainingOutcomePanelProps {
  latestOutcome: TrainingOutcomeView | null;
}

function TrainingOutcomePanel({
  latestOutcome,
}: TrainingOutcomePanelProps) {
  return (
    <article className="training-shell__panel">
      <h2>本轮结果</h2>
      {latestOutcome ? (
        <>
          <dl className="training-shell__summary">
            <div>
              <dt>roundNo</dt>
              <dd>{latestOutcome.roundNo}</dd>
            </div>
            <div>
              <dt>confidence</dt>
              <dd>{latestOutcome.evaluation.confidence}</dd>
            </div>
            <div>
              <dt>evalMode</dt>
              <dd>{latestOutcome.evaluation.evalMode}</dd>
            </div>
            <div>
              <dt>riskFlags</dt>
              <dd>{latestOutcome.evaluation.riskFlags.join(', ') || '无'}</dd>
            </div>
          </dl>

          <div className="training-shell__state-grid">
            <div>
              <h3>Evidence</h3>
              <ul className="training-shell__metric-list">
                {latestOutcome.evaluation.evidence.length > 0 ? (
                  latestOutcome.evaluation.evidence.map((item) => <li key={item}>{item}</li>)
                ) : (
                  <li>无</li>
                )}
              </ul>
            </div>
            <div>
              <h3>Consequence Events</h3>
              <ul className="training-shell__metric-list">
                {latestOutcome.consequenceEvents.length > 0 ? (
                  latestOutcome.consequenceEvents.map((item) => (
                    <li key={`${item.eventType}-${item.summary}`}>
                      {item.label || item.eventType}: {item.summary || '无摘要'}
                    </li>
                  ))
                ) : (
                  <li>本轮暂无额外后果事件。</li>
                )}
              </ul>
            </div>
          </div>
        </>
      ) : (
        <p className="training-shell__empty">
          这里展示最近一次回合提交结果。刷新后只恢复服务端当前会话状态，不回填本地临时评估结果。
        </p>
      )}
    </article>
  );
}

export default TrainingOutcomePanel;
