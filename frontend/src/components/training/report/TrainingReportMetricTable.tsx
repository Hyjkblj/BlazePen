import type { TrainingReportMetric } from '@/types/training';

import { resolveTrainingMetricDisplayLabel } from './trainingMetricLabels';

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

const formatSignedMetric = (value: number): string => {
  const normalized = Number(value.toFixed(2));
  if (normalized > 0) {
    return `+${normalized}`;
  }

  return normalized.toString();
};

interface TrainingReportMetricTableProps {
  title: string;
  metrics: TrainingReportMetric[];
}

function TrainingReportMetricTable({
  title,
  metrics,
}: TrainingReportMetricTableProps) {
  return (
    <div className="training-insight-detail-card">
      <h3>{title}</h3>
      {metrics.length > 0 ? (
        <table className="training-insight-metric-table">
          <thead>
            <tr>
              <th>维度</th>
              <th>开笔</th>
              <th>收官</th>
              <th>起伏</th>
              <th>侧记</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => {
              const labels = [];
              if (metric.isHighestGain) {
                labels.push('峰值进步');
              }
              if (metric.isLowestFinal) {
                labels.push('终局偏弱');
              }
              if (metric.weight !== null) {
                labels.push(`计权 ${formatMetricValue(metric.weight)}`);
              }

              const { primary, codeLine } = resolveTrainingMetricDisplayLabel(metric.code);

              return (
                <tr key={metric.code}>
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
                  <td>{formatMetricValue(metric.initial)}</td>
                  <td>{formatMetricValue(metric.final)}</td>
                  <td>{formatSignedMetric(metric.delta)}</td>
                  <td>{labels.join(' · ') || '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="training-insight-empty">当前没有指标数据。</p>
      )}
    </div>
  );
}

export default TrainingReportMetricTable;
