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
      <h2>学习小结</h2>
      <div className="training-insight-grid">
        <dl className="training-insight-stat-card">
          <dt>完成练习回合</dt>
          <dd>{rounds}</dd>
        </dl>
        <dl className="training-insight-stat-card">
          <dt>能力综合变化</dt>
          <dd>{formatSignedMetric(improvement)}</dd>
        </dl>
        <dl className="training-insight-stat-card">
          <dt>总成绩（加权）</dt>
          <dd>{summary ? formatMetricValue(summary.weightedScoreFinal) : '未提供'}</dd>
        </dl>
        <dl className="training-insight-stat-card">
          <dt>需重点回看回合</dt>
          <dd>{summary?.highRiskRoundCount ?? 0}</dd>
        </dl>
      </div>

      <div className="training-insight-subgrid training-insight-stack-gap">
        <div className="training-insight-detail-card">
          <h3>本次要点</h3>
          <dl className="training-insight-detail-list">
            <div>
              <dt>进步最明显的维度</dt>
              <dd>{summary?.strongestImprovedSkillCode ?? '未提供'}</dd>
            </div>
            <div>
              <dt>仍待加强的维度</dt>
              <dd>{summary?.weakestSkillCode ?? '未提供'}</dd>
            </div>
            <div>
              <dt>出现较多的风险点</dt>
              <dd>{summary?.dominantRiskFlag ?? '未提供'}</dd>
            </div>
            <div>
              <dt>终局评定</dt>
              <dd>{ending ? '已有记录' : '暂无记录'}</dd>
            </div>
          </dl>
        </div>

        <div className="training-insight-detail-card">
          <h3>延伸练习建议</h3>
          {summary?.reviewSuggestions.length ? (
            <ul className="training-insight-code-list">
              {summary.reviewSuggestions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : (
            <p className="training-insight-empty">暂无系统生成的练习建议，可稍后再试刷新，或结合课堂讲义自行安排复习。</p>
          )}
        </div>
      </div>
    </section>
  );
}

export default TrainingReportSummarySection;
