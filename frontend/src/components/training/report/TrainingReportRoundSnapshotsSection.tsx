import type { TrainingReportRoundSnapshot } from '@/types/training';

interface TrainingReportRoundSnapshotsSectionProps {
  snapshots?: TrainingReportRoundSnapshot[];
}

function branchSummary(transition: Record<string, unknown> | null): string {
  if (!transition || Object.keys(transition).length === 0) {
    return '—';
  }
  const src = transition.source_scenario_id;
  const tgt = transition.target_scenario_id;
  if (typeof src === 'string' && typeof tgt === 'string' && (src || tgt)) {
    const reason = transition.reason;
    const reasonPart = typeof reason === 'string' && reason.trim() ? `，${reason}` : '';
    return `${src || '—'} → ${tgt || '—'}${reasonPart}`;
  }
  try {
    return JSON.stringify(transition);
  } catch {
    return '—';
  }
}

function TrainingReportRoundSnapshotsSection({
  snapshots = [],
}: TrainingReportRoundSnapshotsSectionProps) {
  return (
    <details className="training-insight-section training-report-round-snapshots">
      <summary className="training-report-round-snapshots__summary">
        回合聚合快照（「风险标记统计」「推荐分支变化」的数据来源）
      </summary>
      <div className="training-report-round-snapshots__body">
        <p className="training-insight-empty training-report-round-snapshots__hint">
          下表与后端 <code className="training-report-round-snapshots__code">build_report_round_snapshots</code>{' '}
          输出一致。若 <code className="training-report-round-snapshots__code">risk_flags</code> 与{' '}
          <code className="training-report-round-snapshots__code">branch_transition</code> 为空，摘要中的对应统计也会为空。
        </p>
        {!snapshots.length ? (
          <p className="training-insight-empty">当前没有回合快照数据。</p>
        ) : (
          <div className="training-report-round-snapshots__scroll">
            <table className="training-insight-metric-table">
              <thead>
                <tr>
                  <th>回合</th>
                  <th>场景</th>
                  <th>risk_flags</th>
                  <th>branch_transition</th>
                </tr>
              </thead>
              <tbody>
                {snapshots.map((row) => (
                  <tr key={`${row.roundNo}-${row.scenarioId}`}>
                    <td>{row.roundNo}</td>
                    <td>{row.scenarioTitle || row.scenarioId || '—'}</td>
                    <td>{row.riskFlags.length ? row.riskFlags.join('，') : '—'}</td>
                    <td>
                      <span className="training-report-round-snapshots__branch">{branchSummary(row.branchTransition)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </details>
  );
}

export default TrainingReportRoundSnapshotsSection;
