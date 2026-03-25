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
    render(
      <TrainingOutcomePanel
        latestOutcome={latestOutcome}
        mediaTasks={[]}
        mediaTaskFeedStatus="idle"
        mediaTaskFeedErrorMessage={null}
        isPollingMediaTasks={false}
        refreshMediaTasks={() => undefined}
      />
    );

    expect(screen.getByText('Latest Round Outcome')).toBeTruthy();
    expect(screen.getByText('confirmed timeline')).toBeTruthy();
    expect(screen.getByText('Source warning: Source risk increased')).toBeTruthy();
    expect(screen.getByText('selectionSource: manual')).toBeTruthy();
    expect(screen.getByText('recommendedScenarioId: scenario-3')).toBeTruthy();
    expect(screen.getByText('recommendationDiverged: true')).toBeTruthy();
  });

  it('renders empty state when no latest outcome exists', () => {
    render(
      <TrainingOutcomePanel
        latestOutcome={null}
        mediaTasks={[]}
        mediaTaskFeedStatus="idle"
        mediaTaskFeedErrorMessage={null}
        isPollingMediaTasks={false}
        refreshMediaTasks={() => undefined}
      />
    );

    expect(screen.getByText('The latest submitted outcome will appear here.')).toBeTruthy();
  });

  it('renders normalized media task fields without relying on raw payload json', () => {
    render(
      <TrainingOutcomePanel
        latestOutcome={latestOutcome}
        mediaTasks={[
          {
            taskId: 'task-1',
            sessionId: 'session-1',
            roundNo: 2,
            taskType: 'image',
            status: 'succeeded',
            createdAt: null,
            updatedAt: null,
            previewUrl: 'https://example.com/image.png',
            audioUrl: null,
            generatedText: null,
            errorMessage: null,
          },
          {
            taskId: 'task-2',
            sessionId: 'session-1',
            roundNo: 2,
            taskType: 'text',
            status: 'failed',
            createdAt: null,
            updatedAt: null,
            previewUrl: null,
            audioUrl: null,
            generatedText: null,
            errorMessage: 'provider timeout',
          },
        ]}
        mediaTaskFeedStatus="ready"
        mediaTaskFeedErrorMessage={null}
        isPollingMediaTasks={false}
        refreshMediaTasks={() => undefined}
      />
    );

    expect(screen.getByText('https://example.com/image.png')).toBeTruthy();
    expect(screen.getByText('provider timeout')).toBeTruthy();
  });
});
