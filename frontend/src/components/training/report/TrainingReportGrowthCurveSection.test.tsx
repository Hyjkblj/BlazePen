// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingReportGrowthCurveSection from './TrainingReportGrowthCurveSection';

describe('TrainingReportGrowthCurveSection', () => {
  it('renders curve points with high-risk badges and risk flags', () => {
    render(
      <TrainingReportGrowthCurveSection
        growthCurve={[
          {
            roundNo: 2,
            scenarioId: 'S2',
            scenarioTitle: 'Library Pressure',
            kState: {},
            sState: {},
            weightedKScore: 0.72,
            isHighRisk: true,
            riskFlags: ['source_exposure_risk'],
            primarySkillCode: 'K3',
            timestamp: null,
          },
        ]}
      />
    );

    expect(screen.getByText('Round 2')).toBeTruthy();
    expect(screen.getByText('High Risk')).toBeTruthy();
    expect(screen.getByText('Library Pressure')).toBeTruthy();
    expect(screen.getByText('source_exposure_risk')).toBeTruthy();
  });
});
