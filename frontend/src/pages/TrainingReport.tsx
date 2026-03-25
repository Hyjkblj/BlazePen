import { useSearchParams } from 'react-router-dom';
import TrainingReportGrowthCurveSection from '@/components/training/report/TrainingReportGrowthCurveSection';
import TrainingReportHistorySection from '@/components/training/report/TrainingReportHistorySection';
import TrainingReportMetricTable from '@/components/training/report/TrainingReportMetricTable';
import TrainingReportRiskSection from '@/components/training/report/TrainingReportRiskSection';
import TrainingReportStatusNotice from '@/components/training/report/TrainingReportStatusNotice';
import TrainingReportSummarySection from '@/components/training/report/TrainingReportSummarySection';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingReport } from '@/hooks/useTrainingReport';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';

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
          <TrainingReportStatusNotice
            status={data.status}
            hasSummary={Boolean(data.summary)}
          />

          <TrainingReportSummarySection
            rounds={data.rounds}
            improvement={data.improvement}
            summary={data.summary}
            ending={data.ending}
          />

          <TrainingReportRiskSection
            riskFlagCounts={data.summary?.riskFlagCounts ?? []}
            branchTransitions={data.summary?.branchTransitions ?? []}
          />

          <section className="training-insight-section">
            <h2>能力变化与状态变化</h2>
            <div className="training-insight-subgrid">
              <TrainingReportMetricTable
                title="Ability Radar"
                metrics={data.abilityRadar}
              />
              <TrainingReportMetricTable title="State Radar" metrics={data.stateRadar} />
            </div>
          </section>

          <TrainingReportGrowthCurveSection growthCurve={data.growthCurve} />
          <TrainingReportHistorySection history={data.history} />
        </>
      ) : null}
    </TrainingInsightShell>
  );
}

export default TrainingReport;
