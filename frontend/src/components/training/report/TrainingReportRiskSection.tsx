import type { TrainingBranchTransitionSummary, TrainingDiagnosticsCountItem } from '@/types/training';

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
            {item.sourceScenarioId}
            {' -> '}
            {item.targetScenarioId} ({item.transitionType})，触发 {item.count} 次
          {item.reason ? `，原因：${item.reason}` : ''}
          </li>
        ))}
      </ul>
  ) : (
    <p className="training-insight-empty">当前没有分支跳转记录。</p>
  );

interface TrainingReportRiskSectionProps {
  riskFlagCounts: TrainingDiagnosticsCountItem[];
  branchTransitions: TrainingBranchTransitionSummary[];
}

function TrainingReportRiskSection({
  riskFlagCounts,
  branchTransitions,
}: TrainingReportRiskSectionProps) {
  return (
    <section className="training-insight-section">
      <h2>风险与分支概览</h2>
      <div className="training-insight-subgrid">
        <div className="training-insight-detail-card">
          <h3>风险标记统计</h3>
          {renderCountBadges(riskFlagCounts)}
        </div>
        <div className="training-insight-detail-card">
          <h3>推荐分支变化</h3>
          {renderTransitionBadges(branchTransitions)}
        </div>
      </div>
    </section>
  );
}

export default TrainingReportRiskSection;
