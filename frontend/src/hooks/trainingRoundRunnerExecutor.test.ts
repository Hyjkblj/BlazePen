import { describe, expect, it } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import {
  getTrainingRoundNextScenarioErrorMessage,
  getTrainingRoundSubmitErrorMessage,
  isTrainingRoundSessionLevelRecoveryError,
  resolveTrainingRoundRecoveryReason,
} from './trainingRoundRunnerExecutor';

describe('trainingRoundRunnerExecutor', () => {
  it('maps structured submit failures to stable messages', () => {
    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).toBe('提交训练回合超时，请重试。');

    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_COMPLETED',
          message: 'already completed',
        })
      )
    ).toBe('训练已完成，请查看训练报告或重新开始训练。');

    expect(
      getTrainingRoundSubmitErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_NOT_FOUND',
          message: 'session missing',
        })
      )
    ).toBe('训练会话不存在，请重新开始训练。');
  });

  it('maps structured next-scenario failures to recovery messages', () => {
    expect(
      getTrainingRoundNextScenarioErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).toBe('回合已提交，但下一训练场景加载超时，请重试恢复当前训练。');

    expect(
      getTrainingRoundNextScenarioErrorMessage(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'service unavailable',
        })
      )
    ).toBe('回合已提交，但下一训练场景暂时不可用，请重试恢复当前训练。');
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

    expect(isTrainingRoundSessionLevelRecoveryError(duplicateError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(duplicateError)).toBe('duplicate');
    expect(isTrainingRoundSessionLevelRecoveryError(completedError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(completedError)).toBe('completed');
    expect(isTrainingRoundSessionLevelRecoveryError(missingError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(missingError)).toBeNull();
    expect(isTrainingRoundSessionLevelRecoveryError(corruptedError)).toBe(true);
    expect(resolveTrainingRoundRecoveryReason(corruptedError)).toBeNull();
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
