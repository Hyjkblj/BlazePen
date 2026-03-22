import { useSearchParams } from 'react-router-dom';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingReport } from '@/hooks/useTrainingReport';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import type {
  TrainingBranchTransitionSummary,
  TrainingDiagnosticsCountItem,
  TrainingReportMetric,
} from '@/types/training';

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

const formatSignedMetric = (value: number): string => {
  const normalized = Number(value.toFixed(2));
  if (normalized > 0) {
    return `+${normalized}`;
  }

  return normalized.toString();
};

const renderCountBadges = (items: TrainingDiagnosticsCountItem[]) =>
  items.length > 0 ? (
    <ul className="training-insight-badge-list">
      {items.map((item) => (
        <li key={item.code} className="training-insight-badge">
          {item.code}: {item.count}
        </li>
      ))}
    </ul>
  ) : (
    <p className="training-insight-empty">当前没有统计项。</p>
  );

const renderTransitionBadges = (items: TrainingBranchTransitionSummary[]) =>
  items.length > 0 ? (
    <ul className="training-insight-code-list">
      {items.map((item) => (
        <li key={`${item.sourceScenarioId}-${item.targetScenarioId}-${item.reason}`}>
          {item.sourceScenarioId} → {item.targetScenarioId} ({item.transitionType})，触发 {item.count}{' '}
          次
          {item.reason ? `，原因：${item.reason}` : ''}
        </li>
      ))}
    </ul>
  ) : (
    <p className="training-insight-empty">当前没有分支跳转记录。</p>
  );

const renderMetricTable = (title: string, metrics: TrainingReportMetric[]) => (
  <div className="training-insight-detail-card">
    <h3>{title}</h3>
    {metrics.length > 0 ? (
      <table className="training-insight-metric-table">
        <thead>
          <tr>
            <th>指标</th>
            <th>初始</th>
            <th>最终</th>
            <th>变化</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => {
            const labels = [];
            if (metric.isHighestGain) {
              labels.push('最高增益');
            }
            if (metric.isLowestFinal) {
              labels.push('最低最终值');
            }
            if (metric.weight !== null) {
              labels.push(`权重 ${formatMetricValue(metric.weight)}`);
            }

            return (
              <tr key={metric.code}>
                <td>
                  <strong>{metric.code}</strong>
                </td>
                <td>{formatMetricValue(metric.initial)}</td>
                <td>{formatMetricValue(metric.final)}</td>
                <td>{formatSignedMetric(metric.delta)}</td>
                <td>{labels.join(' / ') || '无'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    ) : (
      <p className="training-insight-empty">当前没有指标数据。</p>
    )}
  </div>
);

function TrainingReport() {
  const [searchParams] = useSearchParams();
  const querySessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const { data, status, errorMessage, sessionTarget, hasStaleData, reload } =
    useTrainingReport(querySessionId);

  return (
    <TrainingInsightShell
      title="Training Report"
      description="训练报告页只展示服务端整理后的读模型摘要、能力变化和复盘建议，不在页面层二次拼装 recommendation、audit 或内部快照结构。"
      activeView="report"
      sessionId={sessionTarget.sessionId}
      sessionSource={sessionTarget.source}
      navigationSessionId={querySessionId}
      sessionStatus={data?.status ?? sessionTarget.status}
      loadingMessage={status === 'loading' ? '正在读取训练报告...' : null}
      errorMessage={errorMessage}
      hasStaleData={hasStaleData}
      emptyState={
        !data && !sessionTarget.sessionId
          ? {
              title: '暂无训练报告',
              description:
                '当前没有可读取的训练 sessionId。请先完成一次训练，或从训练主页恢复训练会话后再查看报告。',
            }
          : null
      }
      onRetry={sessionTarget.sessionId ? reload : null}
    >
      {data ? (
        <>
          <section className="training-insight-section">
            <h2>报告摘要</h2>
            <div className="training-insight-grid">
              <dl className="training-insight-stat-card">
                <dt>已完成回合</dt>
                <dd>{data.rounds}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>综合提升</dt>
                <dd>{formatSignedMetric(data.improvement)}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>最终综合分</dt>
                <dd>
                  {data.summary ? formatMetricValue(data.summary.weightedScoreFinal) : '未提供'}
                </dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>高风险回合</dt>
                <dd>{data.summary?.highRiskRoundCount ?? 0}</dd>
              </dl>
            </div>

            <div className="training-insight-subgrid training-insight-stack-gap">
              <div className="training-insight-detail-card">
                <h3>关键结论</h3>
                <dl className="training-insight-detail-list">
                  <div>
                    <dt>最大提升能力</dt>
                    <dd>{data.summary?.strongestImprovedSkillCode ?? '未提供'}</dd>
                  </div>
                  <div>
                    <dt>最低能力</dt>
                    <dd>{data.summary?.weakestSkillCode ?? '未提供'}</dd>
                  </div>
                  <div>
                    <dt>主导风险</dt>
                    <dd>{data.summary?.dominantRiskFlag ?? '未提供'}</dd>
                  </div>
                  <div>
                    <dt>结局结果</dt>
                    <dd>{data.ending ? '已生成' : '未生成'}</dd>
                  </div>
                </dl>
              </div>

              <div className="training-insight-detail-card">
                <h3>复盘建议</h3>
                {data.summary?.reviewSuggestions.length ? (
                  <ul className="training-insight-code-list">
                    {data.summary.reviewSuggestions.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="training-insight-empty">当前没有复盘建议。</p>
                )}
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>风险与分支概览</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>风险标记统计</h3>
                {renderCountBadges(data.summary?.riskFlagCounts ?? [])}
              </div>
              <div className="training-insight-detail-card">
                <h3>推荐分支变化</h3>
                {renderTransitionBadges(data.summary?.branchTransitions ?? [])}
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>能力变化与状态变化</h2>
            <div className="training-insight-subgrid">
              {renderMetricTable('Ability Radar', data.abilityRadar)}
              {renderMetricTable('State Radar', data.stateRadar)}
            </div>
          </section>

          <section className="training-insight-section">
            <h2>成长曲线</h2>
            {data.growthCurve.length > 0 ? (
              <div className="training-insight-timeline">
                {data.growthCurve.map((point) => (
                  <article
                    key={`${point.roundNo}-${point.scenarioId ?? 'initial'}`}
                    className="training-insight-timeline-item"
                  >
                    <div className="training-insight-timeline-item__meta">
                      <span className="training-insight-badge training-insight-badge--warm">
                        Round {point.roundNo}
                      </span>
                      {point.isHighRisk ? (
                        <span className="training-insight-badge training-insight-badge--risk">
                          High Risk
                        </span>
                      ) : null}
                    </div>
                    <h3 className="training-insight-timeline-item__title">{point.scenarioTitle}</h3>
                    <p>
                      场景 ID: {point.scenarioId ?? 'initial'}，综合能力分{' '}
                      {formatMetricValue(point.weightedKScore)}
                      {point.primarySkillCode ? `，主能力 ${point.primarySkillCode}` : ''}
                    </p>
                    {point.riskFlags.length > 0 ? (
                      <ul className="training-insight-badge-list training-insight-stack-gap">
                        {point.riskFlags.map((riskFlag) => (
                          <li
                            key={`${point.roundNo}-${riskFlag}`}
                            className="training-insight-badge training-insight-badge--risk"
                          >
                            {riskFlag}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <p className="training-insight-empty">当前没有成长曲线数据。</p>
            )}
          </section>

          <section className="training-insight-section">
            <h2>回合历史</h2>
            {data.history.length > 0 ? (
              <div className="training-insight-log-list">
                {data.history.map((item) => (
                  <article
                    key={`${item.roundNo}-${item.scenarioId}`}
                    className="training-insight-log-card"
                  >
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
        </>
      ) : null}
    </TrainingInsightShell>
  );
}

export default TrainingReport;
