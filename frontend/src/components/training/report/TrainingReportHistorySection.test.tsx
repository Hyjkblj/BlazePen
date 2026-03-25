// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingReportHistorySection from './TrainingReportHistorySection';

describe('TrainingReportHistorySection', () => {
  it('renders history cards with decision and evaluation details', () => {
    render(
      <TrainingReportHistorySection
        history={[
          {
            roundNo: 1,
            scenarioId: 'S1',
            userInput: 'Protect source and confirm identity',
            selectedOption: 'Option A',
            evaluation: {
              llmModel: 'rules_v1',
              confidence: 0.88,
              riskFlags: ['source_exposure_risk'],
              skillDelta: {},
              stateDelta: {},
              evidence: [],
              skillScoresPreview: {},
              evalMode: 'deterministic',
              fallbackReason: null,
              calibration: null,
              llmRawText: null,
            },
            kStateBefore: {},
            kStateAfter: {},
            sStateBefore: {},
            sStateAfter: {},
            timestamp: null,
            decisionContext: {
              mode: 'guided',
              selectionSource: 'manual',
              selectedScenarioId: 'S1',
              recommendedScenarioId: 'S2',
              candidatePool: [],
              selectedRecommendation: null,
              recommendedRecommendation: null,
              selectedBranchTransition: null,
              recommendedBranchTransition: null,
            },
            ktObservation: {
              scenarioId: 'S1',
              scenarioTitle: 'Initial Briefing',
              trainingMode: 'guided',
              roundNo: 1,
              primarySkillCode: 'K1',
              primaryRiskFlag: 'source_exposure_risk',
              isHighRisk: true,
              targetSkills: [],
              weakSkillsBefore: [],
              riskFlags: ['source_exposure_risk'],
              focusTags: [],
              evidence: [],
              skillObservations: [],
              stateObservations: [],
              observationSummary: '',
            },
            runtimeState: null,
            consequenceEvents: [],
          },
        ]}
      />
    );

    expect(screen.getByText('Round 1')).toBeTruthy();
    expect(screen.getByText('Option A')).toBeTruthy();
    expect(screen.getByText('Protect source and confirm identity')).toBeTruthy();
    expect(screen.getByText('0.88')).toBeTruthy();
    expect(screen.getAllByText('source_exposure_risk').length).toBeGreaterThan(0);
  });
});
