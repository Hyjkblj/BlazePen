// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingReportSummarySection from './TrainingReportSummarySection';

describe('TrainingReportSummarySection', () => {
  it('renders summary metrics and review suggestions', () => {
    render(
      <TrainingReportSummarySection
        rounds={3}
        improvement={0.31}
        ending={{ type: 'completed' }}
        summary={{
          weightedScoreInitial: 0.3,
          weightedScoreFinal: 0.71,
          weightedScoreDelta: 0.41,
          strongestImprovedSkillCode: 'K1',
          strongestImprovedSkillDelta: 0.31,
          weakestSkillCode: 'K2',
          weakestSkillScore: 0.22,
          dominantRiskFlag: 'source_exposure_risk',
          highRiskRoundCount: 1,
          highRiskRoundNos: [2],
          panicTriggerRoundCount: 0,
          sourceExposedRoundCount: 1,
          editorLockedRoundCount: 0,
          highRiskPathRoundCount: 0,
          branchTransitionCount: 1,
          branchTransitionRounds: [2],
          branchTransitions: [],
          riskFlagCounts: [],
          completedScenarioIds: ['S1', 'S2'],
          reviewSuggestions: ['focus-source-safety'],
        }}
      />
    );

    expect(screen.getByText('+0.31')).toBeTruthy();
    expect(screen.getByText('0.71')).toBeTruthy();
    expect(screen.getByText('K1')).toBeTruthy();
    expect(screen.getByText('focus-source-safety')).toBeTruthy();
    expect(screen.getByText('已有记录')).toBeTruthy();
  });
});
