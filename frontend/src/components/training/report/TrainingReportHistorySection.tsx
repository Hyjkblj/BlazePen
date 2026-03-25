import type { TrainingReportHistoryItem } from '@/types/training';

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

interface TrainingReportHistorySectionProps {
  history: TrainingReportHistoryItem[];
}

function TrainingReportHistorySection({ history }: TrainingReportHistorySectionProps) {
  return (
    <section className="training-insight-section">
      <h2>回合历史</h2>
      {history.length > 0 ? (
        <div className="training-insight-log-list">
          {history.map((item) => (
            <article key={`${item.roundNo}-${item.scenarioId}`} className="training-insight-log-card">
              <div className="training-insight-log-card__meta">
                <span className="training-insight-badge training-insight-badge--warm">
                  Round {item.roundNo}
                </span>
                <span className="training-insight-badge">{item.scenarioId}</span>
                {item.ktObservation?.isHighRisk ? (
                  <span className="training-insight-badge training-insight-badge--risk">
                    High Risk
                  </span>
                ) : null}
              </div>
              <h3 className="training-insight-log-card__title">
                {item.ktObservation?.scenarioTitle || item.scenarioId}
              </h3>
              <div className="training-insight-log-card__body">
                <div className="training-insight-subgrid">
                  <div className="training-insight-detail-card">
                    <h3>用户提交</h3>
                    <p>{item.userInput || '未提供'}</p>
                    {item.selectedOption ? (
                      <ul className="training-insight-badge-list training-insight-stack-gap">
                        <li className="training-insight-badge">{item.selectedOption}</li>
                      </ul>
                    ) : null}
                  </div>
                  <div className="training-insight-detail-card">
                    <h3>推荐与选择</h3>
                    <dl className="training-insight-detail-list">
                      <div>
                        <dt>selectionSource</dt>
                        <dd>{item.decisionContext?.selectionSource ?? '未提供'}</dd>
                      </div>
                      <div>
                        <dt>recommendedScenarioId</dt>
                        <dd>{item.decisionContext?.recommendedScenarioId ?? '未提供'}</dd>
                      </div>
                      <div>
                        <dt>selectedScenarioId</dt>
                        <dd>{item.decisionContext?.selectedScenarioId ?? '未提供'}</dd>
                      </div>
                    </dl>
                  </div>
                </div>

                <div className="training-insight-subgrid">
                  <div className="training-insight-detail-card">
                    <h3>评估摘要</h3>
                    {item.evaluation ? (
                      <dl className="training-insight-detail-list">
                        <div>
                          <dt>confidence</dt>
                          <dd>{formatMetricValue(item.evaluation.confidence)}</dd>
                        </div>
                        <div>
                          <dt>evalMode</dt>
                          <dd>{item.evaluation.evalMode}</dd>
                        </div>
                      </dl>
                    ) : (
                      <p className="training-insight-empty">当前回合没有评估摘要。</p>
                    )}
                  </div>

                  <div className="training-insight-detail-card">
                    <h3>风险标记</h3>
                    {item.ktObservation?.riskFlags.length ? (
                      <ul className="training-insight-badge-list">
                        {item.ktObservation.riskFlags.map((riskFlag) => (
                          <li
                            key={`${item.roundNo}-${riskFlag}`}
                            className="training-insight-badge training-insight-badge--risk"
                          >
                            {riskFlag}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="training-insight-empty">当前回合没有风险标记。</p>
                    )}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <p className="training-insight-empty">当前没有回合历史。</p>
      )}
    </section>
  );
}

export default TrainingReportHistorySection;
