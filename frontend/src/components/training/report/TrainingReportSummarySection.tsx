import type { TrainingReportSummary } from '@/types/training';

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

const formatSignedMetric = (value: number): string => {
  const normalized = Number(value.toFixed(2));
  if (normalized > 0) {
    return `+${normalized}`;
  }

  return normalized.toString();
};

interface TrainingReportSummarySectionProps {
  rounds: number;
  improvement: number;
  summary: TrainingReportSummary | null;
  ending: Record<string, unknown> | null;
}

function TrainingReportSummarySection({
  rounds,
  improvement,
  summary,
  ending,
}: TrainingReportSummarySectionProps) {
  return (
    <section className="training-insight-section">
      <h2>报告摘要</h2>
      <div className="training-insight-grid">
        <dl className="training-insight-stat-card">
          <dt>已完成回合</dt>
          <dd>{rounds}</dd>
        </dl>
        <dl className="training-insight-stat-card">
          <dt>综合提升</dt>
          <dd>{formatSignedMetric(improvement)}</dd>
        </dl>
        <dl className="training-insight-stat-card">
          <dt>最终综合分</dt>
          <dd>{summary ? formatMetricValue(summary.weightedScoreFinal) : '未提供'}</dd>
        </dl>
        <dl className="training-insight-stat-card">
          <dt>高风险回合</dt>
          <dd>{summary?.highRiskRoundCount ?? 0}</dd>
        </dl>
      </div>

      <div className="training-insight-subgrid training-insight-stack-gap">
        <div className="training-insight-detail-card">
          <h3>关键结论</h3>
          <dl className="training-insight-detail-list">
            <div>
              <dt>最大提升能力</dt>
              <dd>{summary?.strongestImprovedSkillCode ?? '未提供'}</dd>
            </div>
            <div>
              <dt>最低能力</dt>
              <dd>{summary?.weakestSkillCode ?? '未提供'}</dd>
            </div>
            <div>
              <dt>主导风险</dt>
              <dd>{summary?.dominantRiskFlag ?? '未提供'}</dd>
            </div>
            <div>
              <dt>结局结果</dt>
              <dd>{ending ? '已生成' : '未生成'}</dd>
            </div>
          </dl>
        </div>

        <div className="training-insight-detail-card">
          <h3>复盘建议</h3>
          {summary?.reviewSuggestions.length ? (
            <ul className="training-insight-code-list">
              {summary.reviewSuggestions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="training-insight-empty">当前没有复盘建议。</p>
          )}
        </div>
      </div>
    </section>
  );
}

export default TrainingReportSummarySection;
