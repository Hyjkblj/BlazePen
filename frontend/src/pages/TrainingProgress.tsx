import { useSearchParams } from 'react-router-dom';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingProgress } from '@/hooks/useTrainingProgress';

const formatPercent = (value: number): string => `${Number(value.toFixed(1))}%`;

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

function TrainingProgress() {
  const [searchParams] = useSearchParams();
  const querySessionId = searchParams.get('sessionId');
  const { data, status, errorMessage, sessionTarget, reload } = useTrainingProgress(querySessionId);

  const totalRounds = data?.totalRounds ?? 0;
  const progressPercent =
    data && totalRounds > 0 ? (Math.min(data.roundNo, totalRounds) / totalRounds) * 100 : 0;

  return (
    <TrainingInsightShell
      title="Training Progress"
      description="训练进度页只消费训练查询读模型，不回推会话事实源。刷新后优先读取显式 sessionId，其次读取当前内存活动会话，最后才使用本地恢复入口。"
      activeView="progress"
      sessionId={sessionTarget.sessionId}
      navigationSessionId={querySessionId}
      sessionStatus={data?.status ?? sessionTarget.status}
      loadingMessage={status === 'loading' ? '正在读取训练进度...' : null}
      errorMessage={errorMessage}
      onRetry={sessionTarget.sessionId ? reload : null}
    >
      {!sessionTarget.sessionId ? (
        <section className="training-insight-section">
          <h2>暂无训练会话</h2>
          <p className="training-insight-empty">
            当前没有可读取的训练 sessionId。请先开始训练，或从训练主页恢复最近一次训练会话。
          </p>
        </section>
      ) : null}

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
