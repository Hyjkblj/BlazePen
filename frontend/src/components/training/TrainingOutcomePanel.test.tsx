// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingOutcomePanel from './TrainingOutcomePanel';

const latestOutcome = {
  roundNo: 2,
  evaluation: {
    llmModel: 'rules_v1',
    confidence: 0.86,
    riskFlags: ['source_exposure'],
    skillDelta: {
      verification: 0.2,
    },
    stateDelta: {
      source_safety: -0.05,
    },
    evidence: ['confirmed timeline'],
    skillScoresPreview: {
      verification: 0.72,
    },
    evalMode: 'rules_only',
    fallbackReason: null,
    calibration: null,
    llmRawText: null,
  },
  consequenceEvents: [
    {
      eventType: 'source_warning',
      label: 'Source warning',
      summary: 'Source risk increased',
      severity: 'high',
      roundNo: 2,
      relatedFlag: null,
      stateBar: null,
      payload: {},
    },
  ],
  decisionContext: {
    mode: 'guided' as const,
    selectionSource: 'manual',
    selectedScenarioId: 'scenario-2',
    recommendedScenarioId: 'scenario-3',
    candidatePool: [
      {
        scenarioId: 'scenario-2',
        title: 'Selected',
        rank: 1,
        rankScore: 0.9,
        isSelected: true,
        isRecommended: false,
      },
      {
        scenarioId: 'scenario-3',
        title: 'Recommended',
        rank: 2,
        rankScore: 0.7,
        isSelected: false,
        isRecommended: true,
      },
    ],
    selectedRecommendation: null,
    recommendedRecommendation: null,
    selectedBranchTransition: null,
    recommendedBranchTransition: null,
  },
};

describe('TrainingOutcomePanel', () => {
  it('renders decision context and consequence details for latest outcome', () => {
    render(<TrainingOutcomePanel latestOutcome={latestOutcome} />);

    expect(screen.getByText('Latest Round Outcome')).toBeTruthy();
    expect(screen.getByText('confirmed timeline')).toBeTruthy();
    expect(screen.getByText('Source warning: Source risk increased')).toBeTruthy();
    expect(screen.getByText('selectionSource: manual')).toBeTruthy();
    expect(screen.getByText('recommendedScenarioId: scenario-3')).toBeTruthy();
    expect(screen.getByText('recommendationDiverged: true')).toBeTruthy();
  });

  it('renders empty state when no latest outcome exists', () => {
    render(<TrainingOutcomePanel latestOutcome={null} />);

    expect(screen.getByText('The latest submitted outcome will appear here.')).toBeTruthy();
  });
});
