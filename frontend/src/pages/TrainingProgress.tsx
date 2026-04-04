import { useSearchParams } from 'react-router-dom';
import {
  TRAINING_DECISION_CONTEXT_LABELS,
  TRAINING_RUNTIME_FLAG_LABELS,
  TRAINING_STATE_BAR_LABELS,
  resolveTrainingLabeledField,
  resolveTrainingMetricDisplayLabel,
} from '@/components/training/report/trainingMetricLabels';
import {
  pickDisplayableEndingPayload,
  TrainingInsightEndingBadge,
} from '@/components/training/TrainingInsightEndingBadge';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingProgress } from '@/hooks/useTrainingProgress';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';

const formatPercent = (value: number): string => `${Number(value.toFixed(1))}%`;

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

const formatOptionalValue = (value: string | null | undefined): string =>
  value && value.trim() ? value : '未提供';

const formatBoolCn = (value: boolean): string => (value ? '是' : '否');

function TrainingLabeledCell({
  fieldKey,
  labelMap,
}: {
  fieldKey: string;
  labelMap: Record<string, string>;
}) {
  const { primary, codeLine } = resolveTrainingLabeledField(fieldKey, labelMap);
  return (
    <div className="training-metric-cell">
      <strong className="training-metric-cell__primary">{primary}</strong>
      {codeLine ? (
        <span className="training-metric-cell__code" title={codeLine}>
          {codeLine}
        </span>
      ) : null}
    </div>
  );
}

function TrainingProgress() {
  const [searchParams] = useSearchParams();
  const querySessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const { data, status, errorMessage, sessionTarget, hasStaleData, reload, totalRounds, progressPercent } =
    useTrainingProgress(querySessionId);

  return (
    <TrainingInsightShell
      title="学习进度"
      description="本页展示你当前练到哪一步、最近一轮的决策与后果等，数据来自服务器上的学习记录，不会在浏览器里随意改写。刷新时优先使用网址里的会话编号。下方可展开查看技术会话编号，便于向老师求助。"
      activeView="progress"
      sessionId={sessionTarget.sessionId}
      sessionEnding={data?.ending ?? null}
      sessionIdentity={data?.runtimeState?.playerProfile?.identity ?? null}
      sessionDisplayName={data?.runtimeState?.playerProfile?.name ?? null}
      navigationSessionId={querySessionId}
      sessionStatus={data?.status ?? sessionTarget.status}
      loadingMessage={status === 'loading' ? '正在加载学习进度…' : null}
      errorMessage={errorMessage}
      hasStaleData={hasStaleData}
      emptyState={
        !data && !sessionTarget.sessionId
          ? {
              title: '暂时看不到学习进度',
              description:
                '当前没有可用的学习会话。请先从训练主页开始或恢复最近一次学习。',
            }
          : null
      }
      onRetry={sessionTarget.sessionId ? reload : null}
    >
      {data ? (
        <>
          {(data.status ?? '').toLowerCase() === 'completed' ? (
            <section className="training-insight-section">
              <h2>归档结局</h2>
              {pickDisplayableEndingPayload(data.ending) ? (
                <TrainingInsightEndingBadge ending={data.ending} variant="inline" showExplanation />
              ) : (
                <p className="training-insight-empty">
                  暂未从服务器读到终局分类。可点「刷新读取」，或打开「学习总结」查看是否已写入。
                </p>
              )}
            </section>
          ) : null}

          <section className="training-insight-section training-insight-section--progress-overview">
            <h2>进度总览</h2>
            <div className="training-insight-grid training-insight-grid--progress-summary">
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
                        <dt>
                          <TrainingLabeledCell
                            fieldKey="selectionSource"
                            labelMap={TRAINING_DECISION_CONTEXT_LABELS}
                          />
                        </dt>
                        <dd>{data.decisionContext.selectionSource}</dd>
                      </div>
                      <div>
                        <dt>
                          <TrainingLabeledCell
                            fieldKey="recommendedScenarioId"
                            labelMap={TRAINING_DECISION_CONTEXT_LABELS}
                          />
                        </dt>
                        <dd>{formatOptionalValue(data.decisionContext.recommendedScenarioId)}</dd>
                      </div>
                      <div>
                        <dt>
                          <TrainingLabeledCell
                            fieldKey="selectedScenarioId"
                            labelMap={TRAINING_DECISION_CONTEXT_LABELS}
                          />
                        </dt>
                        <dd>{data.decisionContext.selectedScenarioId}</dd>
                      </div>
                      <div>
                        <dt>
                          <TrainingLabeledCell
                            fieldKey="candidatePool"
                            labelMap={TRAINING_DECISION_CONTEXT_LABELS}
                          />
                        </dt>
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
            <h2>运行时状态</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>简明态势条</h3>
                <dl className="training-insight-detail-list">
                  <div>
                    <dt>
                      <TrainingLabeledCell fieldKey="editorTrust" labelMap={TRAINING_STATE_BAR_LABELS} />
                    </dt>
                    <dd>{formatMetricValue(data.runtimeState.stateBar.editorTrust)}</dd>
                  </div>
                  <div>
                    <dt>
                      <TrainingLabeledCell
                        fieldKey="publicStability"
                        labelMap={TRAINING_STATE_BAR_LABELS}
                      />
                    </dt>
                    <dd>{formatMetricValue(data.runtimeState.stateBar.publicStability)}</dd>
                  </div>
                  <div>
                    <dt>
                      <TrainingLabeledCell fieldKey="sourceSafety" labelMap={TRAINING_STATE_BAR_LABELS} />
                    </dt>
                    <dd>{formatMetricValue(data.runtimeState.stateBar.sourceSafety)}</dd>
                  </div>
                </dl>
              </div>

              <div className="training-insight-detail-card">
                <h3>运行标记</h3>
                <dl className="training-insight-detail-list">
                  <div>
                    <dt>
                      <TrainingLabeledCell
                        fieldKey="panicTriggered"
                        labelMap={TRAINING_RUNTIME_FLAG_LABELS}
                      />
                    </dt>
                    <dd>{formatBoolCn(data.runtimeState.runtimeFlags.panicTriggered)}</dd>
                  </div>
                  <div>
                    <dt>
                      <TrainingLabeledCell
                        fieldKey="sourceExposed"
                        labelMap={TRAINING_RUNTIME_FLAG_LABELS}
                      />
                    </dt>
                    <dd>{formatBoolCn(data.runtimeState.runtimeFlags.sourceExposed)}</dd>
                  </div>
                  <div>
                    <dt>
                      <TrainingLabeledCell
                        fieldKey="editorLocked"
                        labelMap={TRAINING_RUNTIME_FLAG_LABELS}
                      />
                    </dt>
                    <dd>{formatBoolCn(data.runtimeState.runtimeFlags.editorLocked)}</dd>
                  </div>
                  <div>
                    <dt>
                      <TrainingLabeledCell
                        fieldKey="highRiskPath"
                        labelMap={TRAINING_RUNTIME_FLAG_LABELS}
                      />
                    </dt>
                    <dd>{formatBoolCn(data.runtimeState.runtimeFlags.highRiskPath)}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>能力与状态快照</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>八维能力快照</h3>
                {Object.keys(data.runtimeState.kState).length > 0 ? (
                  <table className="training-insight-metric-table">
                    <thead>
                      <tr>
                        <th>维度</th>
                        <th>当前掌握</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.runtimeState.kState).map(([code, value]) => {
                        const { primary, codeLine } = resolveTrainingMetricDisplayLabel(code);
                        return (
                          <tr key={code}>
                            <td>
                              <div className="training-metric-cell">
                                <strong className="training-metric-cell__primary">{primary}</strong>
                                {codeLine ? (
                                  <span className="training-metric-cell__code" title={codeLine}>
                                    {codeLine}
                                  </span>
                                ) : null}
                              </div>
                            </td>
                            <td>{formatMetricValue(value)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <p className="training-insight-empty">当前没有能力快照。</p>
                )}
              </div>

              <div className="training-insight-detail-card">
                <h3>六维态势快照</h3>
                {Object.keys(data.runtimeState.sState).length > 0 ? (
                  <table className="training-insight-metric-table">
                    <thead>
                      <tr>
                        <th>维度</th>
                        <th>当前指数</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(data.runtimeState.sState).map(([code, value]) => {
                        const { primary, codeLine } = resolveTrainingMetricDisplayLabel(code);
                        return (
                          <tr key={code}>
                            <td>
                              <div className="training-metric-cell">
                                <strong className="training-metric-cell__primary">{primary}</strong>
                                {codeLine ? (
                                  <span className="training-metric-cell__code" title={codeLine}>
                                    {codeLine}
                                  </span>
                                ) : null}
                              </div>
                            </td>
                            <td>{formatMetricValue(value)}</td>
                          </tr>
                        );
                      })}
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
