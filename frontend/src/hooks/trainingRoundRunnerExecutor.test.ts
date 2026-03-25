import { describe, expect, it } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import {
  getTrainingRoundNextScenarioErrorMessage,
  getTrainingRoundSubmitErrorMessage,
  isTrainingRoundSessionLevelRecoveryError,
  resolveTrainingRoundRecoveryReason,
} from './trainingRoundRunnerExecutor';

describe('trainingRoundRunnerExecutor', () => {
  it('maps structured submit failures to stable non-fallback messages', () => {
    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).not.toBe('timeout');

    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_COMPLETED',
          message: 'already completed',
        })
      )
    ).not.toBe('already completed');

    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_NOT_FOUND',
          message: 'session missing',
        })
      )
    ).not.toBe('session missing');
  });

  it('maps scenario mismatch to a stable restore prompt', () => {
    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'TRAINING_SCENARIO_MISMATCH',
          message: 'scenario mismatch',
        })
      )
    ).toBe(
      '\u5f53\u524d\u63d0\u4ea4\u573a\u666f\u5df2\u8fc7\u671f\uff0c\u9875\u9762\u5c06\u6309\u670d\u52a1\u7aef\u4f1a\u8bdd\u8fdb\u5ea6\u91cd\u65b0\u6062\u590d\u3002'
    );
  });

  it('maps structured next-scenario failures to stable non-fallback messages', () => {
    expect(
      getTrainingRoundNextScenarioErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).not.toBe('timeout');

    expect(
      getTrainingRoundNextScenarioErrorMessage(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'service unavailable',
        })
      )
    ).not.toBe('service unavailable');
  });

  it('detects session-level recovery errors and resolves recovery reasons', () => {
    const duplicateError = new ServiceError({
      code: 'TRAINING_ROUND_DUPLICATE',
      message: 'duplicate submit',
    });
    const completedError = new ServiceError({
      code: 'TRAINING_SESSION_COMPLETED',
      message: 'already completed',
    });
    const missingError = new ServiceError({
      code: 'TRAINING_SESSION_NOT_FOUND',
      message: 'session missing',
    });
    const corruptedError = new ServiceError({
      code: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
      message: 'state corrupted',
    });
    const mismatchError = new ServiceError({
      code: 'TRAINING_SCENARIO_MISMATCH',
      message: 'scenario mismatch',
    });

    expect(isTrainingRoundSessionLevelRecoveryError(duplicateError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(duplicateError)).toBe('duplicate');
    expect(isTrainingRoundSessionLevelRecoveryError(completedError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(completedError)).toBe('completed');
    expect(isTrainingRoundSessionLevelRecoveryError(missingError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(missingError)).toBeNull();
    expect(isTrainingRoundSessionLevelRecoveryError(corruptedError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(corruptedError)).toBeNull();
    expect(isTrainingRoundSessionLevelRecoveryError(mismatchError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(mismatchError)).toBe('scenario-mismatch');
  });

  it('falls back to default messages and null recovery reason on unknown failures', () => {
    expect(getTrainingRoundSubmitErrorMessage(new Error('submit unstable'))).toBe('submit unstable');
    expect(getTrainingRoundNextScenarioErrorMessage(new Error('next unstable'))).toBe(
      'next unstable'
    );
    expect(isTrainingRoundSessionLevelRecoveryError(new Error('regular failure'))).toBe(false);
    expect(resolveTrainingRoundRecoveryReason(new Error('regular failure'))).toBeNull();
  });
});
