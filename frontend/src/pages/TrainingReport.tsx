import { useSearchParams } from 'react-router-dom';
import TrainingReportGrowthCurveSection from '@/components/training/report/TrainingReportGrowthCurveSection';
import TrainingReportHistorySection from '@/components/training/report/TrainingReportHistorySection';
import TrainingReportMetricTable from '@/components/training/report/TrainingReportMetricTable';
import TrainingReportRiskSection from '@/components/training/report/TrainingReportRiskSection';
import TrainingReportRoundSnapshotsSection from '@/components/training/report/TrainingReportRoundSnapshotsSection';
import TrainingReportStatusNotice from '@/components/training/report/TrainingReportStatusNotice';
import TrainingReportSummarySection from '@/components/training/report/TrainingReportSummarySection';
import { getEndingTypeLabel } from '@/components/training/TrainingInsightEndingBadge';
import TrainingInsightShell from '@/components/training/TrainingInsightShell';
import { useTrainingReport } from '@/hooks/useTrainingReport';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';

function TrainingReport() {
  const [searchParams] = useSearchParams();
  const querySessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const { data, status, errorMessage, sessionTarget, hasStaleData, reload } =
    useTrainingReport(querySessionId);

  const reportTitle = getEndingTypeLabel(data?.ending ?? null) ?? '学习总结';

  return (
    <TrainingInsightShell
      title={reportTitle}
      titleAriaLabel="学习总结"
      description="本页展示你在本轮实训中的学习小结：完成了几轮、能力大致涨落、老师（系统）给出的练习建议等，数据由服务器根据你的作答与规则汇总生成。下方可展开查看会话编号，便于向老师反馈问题。"
      activeView="report"
      sessionId={sessionTarget.sessionId}
      sessionEnding={data?.ending ?? null}
      sessionIdentity={data?.playerProfile?.identity ?? data?.runtimeState?.playerProfile?.identity ?? null}
      sessionDisplayName={data?.playerProfile?.name ?? data?.runtimeState?.playerProfile?.name ?? null}
      navigationSessionId={querySessionId}
      sessionStatus={data?.status ?? sessionTarget.status}
      loadingMessage={status === 'loading' ? '正在加载学习总结…' : null}
      errorMessage={errorMessage}
      hasStaleData={hasStaleData}
      emptyState={
        !data && !sessionTarget.sessionId
          ? {
              title: '暂时看不到学习总结',
              description:
                '当前没有可用的学习会话编号。请先完成一轮实训，或从训练主页恢复最近一次学习后再打开本页。',
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

          <TrainingReportRoundSnapshotsSection snapshots={data.roundSnapshots ?? []} />

          <section className="training-insight-section">
            <h2>能力与情境变化</h2>
            <div className="training-insight-subgrid">
              <TrainingReportMetricTable
                title="八维能力纵览"
                metrics={data.abilityRadar}
              />
              <TrainingReportMetricTable title="六维态势指数" metrics={data.stateRadar} />
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
