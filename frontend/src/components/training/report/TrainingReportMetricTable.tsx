import type { TrainingReportMetric } from '@/types/training';

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
              <th>指标</th>
              <th>初始</th>
              <th>最终</th>
              <th>变化</th>
              <th>说明</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((metric) => {
              const labels = [];
              if (metric.isHighestGain) {
                labels.push('最高增益');
              }
              if (metric.isLowestFinal) {
                labels.push('最低最终值');
              }
              if (metric.weight !== null) {
                labels.push(`权重 ${formatMetricValue(metric.weight)}`);
              }

              return (
                <tr key={metric.code}>
                  <td>
                    <strong>{metric.code}</strong>
                  </td>
                  <td>{formatMetricValue(metric.initial)}</td>
                  <td>{formatMetricValue(metric.final)}</td>
                  <td>{formatSignedMetric(metric.delta)}</td>
                  <td>{labels.join(' / ') || '无'}</td>
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
