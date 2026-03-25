import type { TrainingReportCurvePoint } from '@/types/training';

const formatMetricValue = (value: number): string => Number(value.toFixed(2)).toString();

interface TrainingReportGrowthCurveSectionProps {
  growthCurve: TrainingReportCurvePoint[];
}

function TrainingReportGrowthCurveSection({ growthCurve }: TrainingReportGrowthCurveSectionProps) {
  return (
    <section className="training-insight-section">
      <h2>成长曲线</h2>
      {growthCurve.length > 0 ? (
        <div className="training-insight-timeline">
          {growthCurve.map((point) => (
            <article
              key={`${point.roundNo}-${point.scenarioId ?? 'initial'}`}
              className="training-insight-timeline-item"
            >
              <div className="training-insight-timeline-item__meta">
                <span className="training-insight-badge training-insight-badge--warm">
                  Round {point.roundNo}
                </span>
                {point.isHighRisk ? (
                  <span className="training-insight-badge training-insight-badge--risk">
                    High Risk
                  </span>
                ) : null}
              </div>
              <h3 className="training-insight-timeline-item__title">{point.scenarioTitle}</h3>
              <p>
                场景 ID: {point.scenarioId ?? 'initial'}，综合能力分{' '}
                {formatMetricValue(point.weightedKScore)}
                {point.primarySkillCode ? `，主能力 ${point.primarySkillCode}` : ''}
              </p>
              {point.riskFlags.length > 0 ? (
                <ul className="training-insight-badge-list training-insight-stack-gap">
                  {point.riskFlags.map((riskFlag) => (
                    <li
                      key={`${point.roundNo}-${riskFlag}`}
                      className="training-insight-badge training-insight-badge--risk"
                    >
                      {riskFlag}
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="training-insight-empty">当前没有成长曲线数据。</p>
      )}
    </section>
  );
}

export default TrainingReportGrowthCurveSection;
