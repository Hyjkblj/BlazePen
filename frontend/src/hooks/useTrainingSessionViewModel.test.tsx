// @vitest-environment jsdom

import { renderHook } from '@testing-library/react';
import type { ActiveTrainingSessionState } from '@/contexts';
import type { TrainingResumeTarget } from '@/storage/trainingSessionCache';
import { describe, expect, it } from 'vitest';
import {
  buildTrainingSessionViewFromSummary,
  resolveTrainingSessionRestoreIdentity,
  resolveTrainingSessionWorkspaceSeed,
  useTrainingSessionViewModel,
} from './useTrainingSessionViewModel';

const createRuntimeState = (sceneId: string, roundNo: number) => ({
  currentRoundNo: roundNo,
  currentSceneId: sceneId,
  kState: {
    K1: 0.42,
  },
  sState: {
    source_safety: 0.88,
  },
  runtimeFlags: {
    panicTriggered: false,
    sourceExposed: false,
    editorLocked: false,
    highRiskPath: false,
  },
  stateBar: {
    editorTrust: 0.72,
    publicStability: 0.81,
    sourceSafety: 0.88,
  },
  playerProfile: null,
});

const createScenario = (id: string, title: string) => ({
  id,
  title,
  eraDate: '1941-06-14',
  location: 'Shanghai',
  brief: `${title} brief`,
  mission: 'Protect the source while filing the story.',
  decisionFocus: 'Choose the safest next move.',
  targetSkills: ['verification'],
  riskTags: ['exposure'],
  options: [],
  completionHint: '',
  recommendation: null,
});

const createSummary = (sessionId: string) => ({
  sessionId,
  trainingMode: 'adaptive' as const,
  status: 'in_progress',
  roundNo: 2,
  totalRounds: 6,
  runtimeState: createRuntimeState('scenario-summary', 2),
  progressAnchor: {
    roundNo: 2,
    totalRounds: 6,
    completedRounds: 2,
    remainingRounds: 4,
    progressPercent: 33.3,
    nextRoundNo: 3,
  },
  resumableScenario: createScenario('scenario-summary', 'Restore Scenario'),
  scenarioCandidates: [createScenario('candidate-1', 'Candidate 1')],
  canResume: true,
  isCompleted: false,
  createdAt: '2026-03-22T10:00:00Z',
  updatedAt: '2026-03-22T10:05:00Z',
  endTime: null,
});

describe('useTrainingSessionViewModel', () => {
  it('builds a session view directly from the training summary contract', () => {
    const sessionView = buildTrainingSessionViewFromSummary(
      createSummary('training-session-summary'),
      '42'
    );

    expect(sessionView).toMatchObject({
      sessionId: 'training-session-summary',
      trainingMode: 'adaptive',
      characterId: '42',
      roundNo: 2,
      canResume: true,
      isCompleted: false,
    });
    expect(sessionView.currentScenario?.id).toBe('scenario-summary');
    expect(sessionView.progressAnchor?.progressPercent).toBe(33.3);
  });

  it('prefers the current session view when resolving a manual restore target', () => {
    const sessionView = buildTrainingSessionViewFromSummary(
      createSummary('training-session-1'),
      '99'
    );
    const activeSession: ActiveTrainingSessionState = {
      sessionId: 'training-session-1',
      trainingMode: 'guided',
      characterId: '42',
      status: 'in_progress',
      roundNo: 2,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-active', 2),
    };
    const resumeTarget: TrainingResumeTarget = {
      sessionId: 'training-session-1',
      trainingMode: 'self-paced',
      characterId: '11',
      status: 'in_progress',
      timestamp: 1711092000000,
    };

    const restoreIdentity = resolveTrainingSessionRestoreIdentity({
      explicitSessionId: 'training-session-1',
      sessionView,
      activeSession,
      resumeTarget,
    });

    expect(restoreIdentity).toEqual({
      sessionId: 'training-session-1',
      trainingMode: 'adaptive',
      characterId: '99',
      source: 'session-view',
    });
  });

  it('uses activeSession as the primary workspace seed and keeps resumeTarget as fallback', () => {
    const activeSession: ActiveTrainingSessionState = {
      sessionId: 'training-session-active',
      trainingMode: 'adaptive',
      characterId: '42',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-active', 1),
    };
    const resumeTarget: TrainingResumeTarget = {
      sessionId: 'training-session-stale',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
      timestamp: 1711092000000,
    };

    expect(
      resolveTrainingSessionWorkspaceSeed({
        sessionView: null,
        activeSession,
        resumeTarget,
      })
    ).toEqual({
      currentSessionId: 'training-session-active',
      currentSessionSource: 'active-session',
      autoRestoreSessionId: 'training-session-active',
      preferredTrainingMode: 'adaptive',
      preferredCharacterId: '42',
    });
  });

  it('stops auto restore after a session view is present but still restores from the current session', () => {
    const sessionView = buildTrainingSessionViewFromSummary(
      createSummary('training-session-view'),
      '77'
    );
    const activeSession: ActiveTrainingSessionState = {
      sessionId: 'training-session-active',
      trainingMode: 'guided',
      characterId: '42',
      status: 'in_progress',
      roundNo: 1,
      totalRounds: 6,
      runtimeState: createRuntimeState('scenario-active', 1),
    };
    const resumeTarget: TrainingResumeTarget = {
      sessionId: 'training-session-stale',
      trainingMode: 'self-paced',
      characterId: '11',
      status: 'in_progress',
      timestamp: 1711092000000,
    };

    const { result } = renderHook(() =>
      useTrainingSessionViewModel({
        sessionView,
        activeSession,
        resumeTarget,
      })
    );

    expect(result.current.currentSessionId).toBe('training-session-view');
    expect(result.current.currentSessionSource).toBe('session-view');
    expect(result.current.autoRestoreSessionId).toBeNull();
    expect(result.current.preferredTrainingMode).toBe('adaptive');
    expect(result.current.preferredCharacterId).toBe('77');
    expect(result.current.resolveRestoreIdentity('training-session-view')).toMatchObject({
      sessionId: 'training-session-view',
      source: 'session-view',
      characterId: '77',
    });
  });

  it('keeps the homepage insight entry on the same target selector as the read pages', () => {
    const resumeTarget: TrainingResumeTarget = {
      sessionId: 'training-session-resume',
      trainingMode: 'guided',
      characterId: '11',
      status: 'in_progress',
      timestamp: 1711092000000,
    };

    expect(
      resolveTrainingSessionWorkspaceSeed({
        sessionView: null,
        activeSession: null,
        resumeTarget,
      })
    ).toEqual({
      currentSessionId: 'training-session-resume',
      currentSessionSource: 'resume-target',
      autoRestoreSessionId: 'training-session-resume',
      preferredTrainingMode: 'guided',
      preferredCharacterId: '11',
    });
  });
});
