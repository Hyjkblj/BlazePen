import { useSearchParams } from 'react-router-dom';
import {
  pickDisplayableEndingPayload,
  TrainingInsightEndingBadge,
} from '@/components/training/TrainingInsightEndingBadge';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingDiagnostics } from '@/hooks/useTrainingDiagnostics';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import type {
  TrainingBranchTransitionSummary,
  TrainingDiagnosticsCountItem,
  TrainingKtObservation,
  TrainingRecommendationLog,
} from '@/types/training';

const formatCountBadges = (items: TrainingDiagnosticsCountItem[]) =>
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

const renderBranchTransitionList = (items: TrainingBranchTransitionSummary[]) =>
  items.length > 0 ? (
    <ul className="training-insight-code-list">
      {items.map((item) => (
        <li key={`${item.sourceScenarioId}-${item.targetScenarioId}-${item.count}`}>
          {item.sourceScenarioId} → {item.targetScenarioId}，触发 {item.count} 次
          {item.triggeredFlags.length > 0 ? `，flags: ${item.triggeredFlags.join(', ')}` : ''}
        </li>
      ))}
    </ul>
  ) : (
    <p className="training-insight-empty">当前没有分支跳转诊断。</p>
  );

const renderRecommendationLog = (log: TrainingRecommendationLog) => (
  <article key={log.roundNo} className="training-insight-log-card">
    <div className="training-insight-log-card__meta">
      <span className="training-insight-badge training-insight-badge--warm">
        Round {log.roundNo}
      </span>
      <span className="training-insight-badge">{log.trainingMode}</span>
      {log.selectionSource ? (
        <span className="training-insight-badge">{log.selectionSource}</span>
      ) : null}
    </div>
    <h3 className="training-insight-log-card__title">推荐决策日志</h3>
    <div className="training-insight-log-card__body">
      <div className="training-insight-subgrid">
        <div className="training-insight-detail-card">
          <h3>推荐与选择</h3>
          <dl className="training-insight-detail-list">
            <div>
              <dt>recommendedScenarioId</dt>
              <dd>{log.recommendedScenarioId ?? '未提供'}</dd>
            </div>
            <div>
              <dt>selectedScenarioId</dt>
              <dd>{log.selectedScenarioId ?? '未提供'}</dd>
            </div>
            <div>
              <dt>candidatePool</dt>
              <dd>{log.candidatePool.length}</dd>
            </div>
          </dl>
        </div>

        <div className="training-insight-detail-card">
          <h3>推荐分支</h3>
          <dl className="training-insight-detail-list">
            <div>
              <dt>recommended rank score</dt>
              <dd>{log.recommendedRecommendation?.rankScore ?? '未提供'}</dd>
            </div>
            <div>
              <dt>selected rank score</dt>
              <dd>{log.selectedRecommendation?.rankScore ?? '未提供'}</dd>
            </div>
            <div>
              <dt>decision source</dt>
              <dd>{log.decisionContext?.selectionSource ?? '未提供'}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  </article>
);

const renderObservation = (observation: TrainingKtObservation) => (
  <article
    key={`${observation.roundNo ?? 'na'}-${observation.scenarioId}`}
    className="training-insight-log-card"
  >
    <div className="training-insight-log-card__meta">
      <span className="training-insight-badge training-insight-badge--warm">
        Round {observation.roundNo ?? 'N/A'}
      </span>
      <span className="training-insight-badge">{observation.trainingMode}</span>
      {observation.isHighRisk ? (
        <span className="training-insight-badge training-insight-badge--risk">High Risk</span>
      ) : null}
    </div>
    <h3 className="training-insight-log-card__title">{observation.scenarioTitle}</h3>
    <div className="training-insight-log-card__body">
      <div className="training-insight-subgrid">
        <div className="training-insight-detail-card">
          <h3>观测摘要</h3>
          <p>{observation.observationSummary || '未提供'}</p>
        </div>
        <div className="training-insight-detail-card">
          <h3>能力与风险</h3>
          {observation.riskFlags.length > 0 ? (
            <ul className="training-insight-badge-list">
              {observation.riskFlags.map((riskFlag) => (
                <li
                  key={`${observation.scenarioId}-${riskFlag}`}
                  className="training-insight-badge training-insight-badge--risk"
                >
                  {riskFlag}
                </li>
              ))}
            </ul>
          ) : (
            <p className="training-insight-empty">当前没有风险标记。</p>
          )}
        </div>
      </div>
    </div>
  </article>
);

function TrainingDiagnostics() {
  const [searchParams] = useSearchParams();
  const querySessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const { data, status, errorMessage, sessionTarget, hasStaleData, reload } =
    useTrainingDiagnostics(querySessionId);

  return (
    <TrainingInsightShell
      title="学情诊断"
      description="本页用图表和列表帮你看到：系统在哪些环节给了推荐、出现过哪些风险标签等，便于对照课堂要求自查。数据全部由服务器汇总，前端不做「猜结论」。下方可展开查看会话编号。"
      activeView="diagnostics"
      sessionId={sessionTarget.sessionId}
      sessionEnding={data?.ending ?? null}
      sessionIdentity={data?.playerProfile?.identity ?? data?.runtimeState?.playerProfile?.identity ?? null}
      sessionDisplayName={data?.playerProfile?.name ?? data?.runtimeState?.playerProfile?.name ?? null}
      navigationSessionId={querySessionId}
      sessionStatus={data?.status ?? sessionTarget.status}
      loadingMessage={status === 'loading' ? '正在加载学情诊断…' : null}
      errorMessage={errorMessage}
      hasStaleData={hasStaleData}
      emptyState={
        !data && !sessionTarget.sessionId
          ? {
              title: '暂时看不到学情诊断',
              description:
                '当前没有可用的学习会话。请先开始实训，或从训练主页恢复后再打开本页。',
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

          <section className="training-insight-section training-insight-section--diagnostics-summary">
            <h2>诊断摘要</h2>
            <div className="training-insight-grid">
              <dl className="training-insight-stat-card">
                <dt>推荐日志</dt>
                <dd>{data.summary?.totalRecommendationLogs ?? 0}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>审计事件</dt>
                <dd>{data.summary?.totalAuditEvents ?? 0}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>KT 观测</dt>
                <dd>{data.summary?.totalKtObservations ?? 0}</dd>
              </dl>
              <dl className="training-insight-stat-card">
                <dt>推荐与作答不一致</dt>
                <dd>{data.summary?.recommendedVsSelectedMismatchCount ?? 0}</dd>
              </dl>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>风险与计数聚合</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>风险标记</h3>
                {formatCountBadges(data.summary?.riskFlagCounts ?? [])}
              </div>
              <div className="training-insight-detail-card">
                <h3>关注能力</h3>
                {formatCountBadges(data.summary?.primarySkillFocusCounts ?? [])}
              </div>
              <div className="training-insight-detail-card">
                <h3>选择来源</h3>
                {formatCountBadges(data.summary?.selectionSourceCounts ?? [])}
              </div>
              <div className="training-insight-detail-card">
                <h3>事件类型</h3>
                {formatCountBadges(data.summary?.eventTypeCounts ?? [])}
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>分支与阶段诊断</h2>
            <div className="training-insight-subgrid">
              <div className="training-insight-detail-card">
                <h3>分支跳转</h3>
                {renderBranchTransitionList(data.summary?.branchTransitions ?? [])}
              </div>
              <div className="training-insight-detail-card">
                <h3>阶段标签</h3>
                {formatCountBadges(data.summary?.phaseTagCounts ?? [])}
              </div>
            </div>
          </section>

          <section className="training-insight-section">
            <h2>推荐日志</h2>
            {data.recommendationLogs.length > 0 ? (
              <div className="training-insight-log-list">
                {data.recommendationLogs.map((log) => renderRecommendationLog(log))}
              </div>
            ) : (
              <p className="training-insight-empty">当前没有推荐日志。</p>
            )}
          </section>

          <section className="training-insight-section">
            <h2>KT 观测</h2>
            {data.ktObservations.length > 0 ? (
              <div className="training-insight-log-list">
                {data.ktObservations.map((observation) => renderObservation(observation))}
              </div>
            ) : (
              <p className="training-insight-empty">当前没有 KT 观测。</p>
            )}
          </section>

          <section className="training-insight-section">
            <h2>审计事件</h2>
            {data.auditEvents.length > 0 ? (
              <ul className="training-insight-code-list">
                {data.auditEvents.map((event, index) => (
                  <li key={`${event.eventType}-${event.roundNo ?? 'na'}-${index}`}>
                    {event.eventType}
                    {event.roundNo !== null ? `，round ${event.roundNo}` : ''}
                    {event.timestamp ? `，${event.timestamp}` : ''}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="training-insight-empty">当前没有审计事件。</p>
            )}
          </section>
        </>
      ) : null}
    </TrainingInsightShell>
  );
}

export default TrainingDiagnostics;
