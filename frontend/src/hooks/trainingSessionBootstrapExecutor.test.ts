import { describe, expect, it } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import {
  getTrainingRestoreErrorMessage,
  getTrainingStartErrorMessage,
  resolveTrainingRestoreFailureState,
} from './trainingSessionBootstrapExecutor';

describe('trainingSessionBootstrapExecutor', () => {
  it('maps structured restore errors to stable restore messages', () => {
    expect(
      getTrainingRestoreErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_NOT_FOUND',
          message: 'session missing',
        })
      )
    ).toBe('训练会话不存在，已清理本地恢复入口。');

    expect(
      getTrainingRestoreErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
          message: 'state corrupted',
        })
      )
    ).toBe('训练会话恢复状态损坏，已清理本地恢复入口。');

    expect(
      getTrainingRestoreErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).toBe('训练恢复超时，请重试。');
  });

  it('resolves terminal restore failures for recovery artifact cleanup', () => {
    expect(
      resolveTrainingRestoreFailureState(
        new ServiceError({
          code: 'TRAINING_SESSION_NOT_FOUND',
          message: 'session missing',
        })
      )
    ).toEqual({
      errorMessage: '训练会话不存在，已清理本地恢复入口。',
      shouldClearRecoveryArtifacts: true,
    });

    expect(
      resolveTrainingRestoreFailureState(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'service unavailable',
        })
      )
    ).toEqual({
      errorMessage: '训练恢复服务暂时不可用，请稍后重试。',
      shouldClearRecoveryArtifacts: false,
    });
  });

  it('maps structured init failures to stable start messages', () => {
    expect(
      getTrainingStartErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).toBe('训练初始化超时，请重试。');

    expect(
      getTrainingStartErrorMessage(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'service unavailable',
        })
      )
    ).toBe('训练初始化服务暂时不可用，请稍后重试。');
  });

  it('falls back to original service message for unknown bootstrap failures', () => {
    expect(getTrainingStartErrorMessage(new Error('bootstrap unstable'))).toBe(
      'bootstrap unstable'
    );
    expect(getTrainingRestoreErrorMessage(new Error('restore unstable'))).toBe(
      'restore unstable'
    );
  });
});
