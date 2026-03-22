import type { ActiveTrainingSessionState } from '@/contexts';
import type { TrainingResumeTarget } from '@/storage/trainingSessionCache';
import { describe, expect, it } from 'vitest';
import {
  normalizeTrainingSessionId,
  resolveTrainingSessionReadTarget,
} from './useTrainingSessionReadTarget';

const createActiveSession = (
  overrides: Partial<ActiveTrainingSessionState> = {}
): ActiveTrainingSessionState => ({
  sessionId: 'training-session-active',
  trainingMode: 'guided',
  characterId: 'character-active',
  status: 'in_progress',
  roundNo: 2,
  totalRounds: 6,
  runtimeState: {
    currentRoundNo: 2,
    currentSceneId: 'scenario-active',
    kState: {},
    sState: {},
    runtimeFlags: {
      panicTriggered: false,
      sourceExposed: false,
      editorLocked: false,
      highRiskPath: false,
    },
    stateBar: {
      editorTrust: 0.7,
      publicStability: 0.8,
      sourceSafety: 0.9,
    },
    playerProfile: null,
  },
  ...overrides,
});

const createResumeTarget = (
  overrides: Partial<TrainingResumeTarget> = {}
): TrainingResumeTarget => ({
  sessionId: 'training-session-resume',
  trainingMode: 'adaptive',
  characterId: 'character-resume',
  status: 'completed',
  timestamp: 1711092000000,
  ...overrides,
});

describe('resolveTrainingSessionReadTarget', () => {
  it('normalizes dirty query sessionId sentinels case-insensitively', () => {
    expect(normalizeTrainingSessionId(' undefined ')).toBeNull();
    expect(normalizeTrainingSessionId(' NULL ')).toBeNull();
    expect(normalizeTrainingSessionId(' training-session-1 ')).toBe('training-session-1');
  });

  it('prioritizes explicit sessionId over activeSession and resumeTarget', () => {
    expect(
      resolveTrainingSessionReadTarget({
        explicitSessionId: 'training-session-explicit',
        activeSession: createActiveSession(),
        resumeTarget: createResumeTarget(),
      })
    ).toEqual({
      sessionId: 'training-session-explicit',
      trainingMode: null,
      characterId: null,
      status: null,
      source: 'explicit',
    });
  });

  it('hydrates explicit session metadata when it matches activeSession', () => {
    expect(
      resolveTrainingSessionReadTarget({
        explicitSessionId: 'training-session-active',
        activeSession: createActiveSession({
          trainingMode: 'self-paced',
          characterId: 'character-42',
        }),
        resumeTarget: createResumeTarget(),
      })
    ).toEqual({
      sessionId: 'training-session-active',
      trainingMode: 'self-paced',
      characterId: 'character-42',
      status: 'in_progress',
      source: 'explicit',
    });
  });

  it('falls back to activeSession when explicit sessionId is a dirty sentinel', () => {
    expect(
      resolveTrainingSessionReadTarget({
        explicitSessionId: ' undefined ',
        activeSession: createActiveSession(),
        resumeTarget: createResumeTarget(),
      })
    ).toEqual({
      sessionId: 'training-session-active',
      trainingMode: 'guided',
      characterId: 'character-active',
      status: 'in_progress',
      source: 'active-session',
    });
  });

  it('ignores dirty activeSession ids and falls back to resumeTarget', () => {
    expect(
      resolveTrainingSessionReadTarget({
        activeSession: createActiveSession({
          sessionId: ' null ',
          characterId: 'undefined',
        }),
        resumeTarget: createResumeTarget(),
      })
    ).toEqual({
      sessionId: 'training-session-resume',
      trainingMode: 'adaptive',
      characterId: 'character-resume',
      status: 'completed',
      source: 'resume-target',
    });
  });

  it('returns none when all session ids are missing or dirty', () => {
    expect(
      resolveTrainingSessionReadTarget({
        explicitSessionId: 'null',
        activeSession: createActiveSession({
          sessionId: 'undefined',
        }),
        resumeTarget: createResumeTarget({
          sessionId: '  ',
          characterId: 'null',
        }),
      })
    ).toEqual({
      sessionId: null,
      trainingMode: null,
      characterId: null,
      status: null,
      source: 'none',
    });
  });
});
