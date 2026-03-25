// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingReportRiskSection from './TrainingReportRiskSection';

describe('TrainingReportRiskSection', () => {
  it('renders risk counts and branch transitions', () => {
    render(
      <TrainingReportRiskSection
        riskFlagCounts={[
          {
            code: 'source_exposure_risk',
            count: 2,
          },
        ]}
        branchTransitions={[
          {
            sourceScenarioId: 'S1',
            targetScenarioId: 'S2',
            transitionType: 'branch',
            reason: 'source_warning',
            count: 1,
            roundNos: [2],
            triggeredFlags: ['source_warning'],
          },
        ]}
      />
    );

    expect(screen.getByText('source_exposure_risk: 2')).toBeTruthy();
    expect(
      screen.getByText('S1 -> S2 (branch)，触发 1 次，原因：source_warning')
    ).toBeTruthy();
  });
});
