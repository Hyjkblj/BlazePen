import { describe, expect, it } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import {
  getTrainingReadErrorMessage,
  resolveTrainingReadFailureState,
} from './trainingReadQueryExecutor';

describe('trainingReadQueryExecutor', () => {
  it('maps structured training errors to stable read-query messages', () => {
    expect(
      getTrainingReadErrorMessage(
        new ServiceError({
          code: 'TRAINING_SESSION_NOT_FOUND',
          message: 'session missing',
        }),
        'fallback'
      )
    ).toBe('训练会话不存在，请返回训练主页重新开始。');

    expect(
      getTrainingReadErrorMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        }),
        'fallback'
      )
    ).toBe('训练结果读取超时，请重试。');
  });

  it('marks terminal recovery errors for cache cleanup and data reset', () => {
    const state = resolveTrainingReadFailureState({
      error: new ServiceError({
        code: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
        message: 'state corrupted',
      }),
      fallbackMessage: 'fallback',
      hasCurrentSessionData: true,
    });

    expect(state).toEqual({
      errorCode: 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
      errorMessage: '训练会话恢复状态损坏，当前结果无法读取。',
      shouldClearData: true,
      shouldClearRecoveryArtifacts: true,
    });
  });

  it('keeps stale data on transient failures when current session data exists', () => {
    const state = resolveTrainingReadFailureState({
      error: new ServiceError({
        code: 'SERVICE_UNAVAILABLE',
        message: 'service unavailable',
      }),
      fallbackMessage: 'fallback',
      hasCurrentSessionData: true,
    });

    expect(state).toEqual({
      errorCode: 'SERVICE_UNAVAILABLE',
      errorMessage: '训练结果服务暂时不可用，请稍后重试。',
      shouldClearData: false,
      shouldClearRecoveryArtifacts: false,
    });
  });
});
