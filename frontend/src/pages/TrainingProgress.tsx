import { useSearchParams } from 'react-router-dom';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingProgress } from '@/hooks/useTrainingProgress';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';

const formatPercent = (value: number): string => `${Number(value.toFixed(1))}%`;

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

const formatOptionalValue = (value: string | null | undefined): string =>
  value && value.trim() ? value : '未提供';

function TrainingProgress() {
  const [searchParams] = useSearchParams();
  const querySessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const { data, status, errorMessage, sessionTarget, hasStaleData, reload, totalRounds, progressPercent } =
    useTrainingProgress(querySessionId);

  return (
    <TrainingInsightShell
      title="Training Progress"
      description="训练进度页只消费训练查询读模型，不回推会话事实源。刷新后优先读取显式 sessionId，其次读取当前内存活动会话；本地恢复入口仅用于手动恢复提示。"
      activeView="progress"
      sessionId={sessionTarget.sessionId}
      sessionSource={sessionTarget.source}
      navigationSessionId={querySessionId}
      sessionStatus={data?.status ?? sessionTarget.status}
      loadingMessage={status === 'loading' ? '正在读取训练进度...' : null}
      errorMessage={errorMessage}
      hasStaleData={hasStaleData}
      emptyState={
        !data && !sessionTarget.sessionId
          ? {
              title: '暂无训练进度',
              description:
                '当前没有可读取的训练 sessionId。请先开始训练，或从训练主页恢复最近一次训练会话。',
            }
          : null
      }
      onRetry={sessionTarget.sessionId ? reload : null}
    >
      {data ? (
        <>
          <section className="training-insight-section">
            <h2>进度总览</h2>
            <div className="training-insight-grid">
              <dl className="training-insight-stat-card">
                <dt>当前回合</dt>
                <dd>{data.roundNo}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>总回合数</dt>
                <dd>{totalRounds || '未提供'}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>完成进度</dt>
                <dd>{formatPercent(progressPercent)}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>当前场景</dt>
                <dd>{data.runtimeState.currentSceneId ?? '暂无'}</dd>
              </dl>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>最近决策影响</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>决策上下文</h3>
                {data.decisionContext ? (
                  <>
                    <dl className="training-insight-detail-list">
                      <div>
                        <dt>selectionSource</dt>
                        <dd>{data.decisionContext.selectionSource}</dd>
                      </div>
                      <div>
                        <dt>recommendedScenarioId</dt>
                        <dd>{formatOptionalValue(data.decisionContext.recommendedScenarioId)}</dd>
                      </div>
                      <div>
                        <dt>selectedScenarioId</dt>
                        <dd>{data.decisionContext.selectedScenarioId}</dd>
                      </div>
                      <div>
                        <dt>candidatePool</dt>
                        <dd>{data.decisionContext.candidatePool.length}</dd>
                      </div>
                    </dl>
                    {data.decisionContext.selectedBranchTransition ? (
                      <ul className="training-insight-code-list">
                        <li>
                          {data.decisionContext.selectedBranchTransition.sourceScenarioId}
                          {' -> '}
                          {data.decisionContext.selectedBranchTransition.targetScenarioId}
                          {' ('}
                          {data.decisionContext.selectedBranchTransition.transitionType}
                          {')'}
                          {data.decisionContext.selectedBranchTransition.reason
                            ? `，原因：${data.decisionContext.selectedBranchTransition.reason}`
                            : ''}
                        </li>
                      </ul>
                    ) : (
                      <p className="training-insight-empty">当前回合没有触发分支跳转。</p>
                    )}
                  </>
                ) : (
                  <p className="training-insight-empty">当前没有决策上下文。</p>
                )}
              </div>

              <div className="training-insight-detail-card">
                <h3>后果事件</h3>
                {(data.consequenceEvents ?? []).length > 0 ? (
                  <ul className="training-insight-code-list">
                    {(data.consequenceEvents ?? []).map((event, index) => (
                      <li key={`${event.eventType}-${event.roundNo ?? 'na'}-${index}`}>
                        {event.label || event.eventType}
                        {` (${event.severity})`}
                        {event.summary ? `：${event.summary}` : ''}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="training-insight-empty">当前回合没有后果事件。</p>
                )}
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>Runtime State</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>State Bar</h3>
                <dl className="training-insight-detail-list">
                  <div>
                    <dt>editorTrust</dt>
                    <dd>{formatMetricValue(data.runtimeState.stateBar.editorTrust)}</dd>
                  </div>
                  <div>
                    <dt>publicStability</dt>
                    <dd>{formatMetricValue(data.runtimeState.stateBar.publicStability)}</dd>
                  </div>
                  <div>
                    <dt>sourceSafety</dt>
                    <dd>{formatMetricValue(data.runtimeState.stateBar.sourceSafety)}</dd>
                  </div>
                </dl>
              </div>

              <div className="training-insight-detail-card">
                <h3>Runtime Flags</h3>
                <dl className="training-insight-detail-list">
                  <div>
                    <dt>panicTriggered</dt>
                    <dd>{String(data.runtimeState.runtimeFlags.panicTriggered)}</dd>
                  </div>
                  <div>
                    <dt>sourceExposed</dt>
                    <dd>{String(data.runtimeState.runtimeFlags.sourceExposed)}</dd>
                  </div>
                  <div>
                    <dt>editorLocked</dt>
                    <dd>{String(data.runtimeState.runtimeFlags.editorLocked)}</dd>
                  </div>
                  <div>
                    <dt>highRiskPath</dt>
                    <dd>{String(data.runtimeState.runtimeFlags.highRiskPath)}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>能力与状态快照</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>K State</h3>
                {Object.keys(data.runtimeState.kState).length > 0 ? (
                  <table className="training-insight-metric-table">
                    <thead>
                      <tr>
                        <th>能力编码</th>
                        <th>当前值</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.runtimeState.kState).map(([code, value]) => (
                        <tr key={code}>
                          <td>
                            <strong>{code}</strong>
                          </td>
                          <td>{formatMetricValue(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="training-insight-empty">当前没有能力快照。</p>
                )}
              </div>

              <div className="training-insight-detail-card">
                <h3>S State</h3>
                {Object.keys(data.runtimeState.sState).length > 0 ? (
                  <table className="training-insight-metric-table">
                    <thead>
                      <tr>
                        <th>状态编码</th>
                        <th>当前值</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.runtimeState.sState).map(([code, value]) => (
                        <tr key={code}>
                          <td>
                            <strong>{code}</strong>
                          </td>
                          <td>{formatMetricValue(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="training-insight-empty">当前没有状态快照。</p>
                )}
              </div>
            </div>
          </section>
        </>
      ) : null}
    </TrainingInsightShell>
  );
}

export default TrainingProgress;
