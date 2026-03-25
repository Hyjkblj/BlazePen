import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';

const SESSION_LEVEL_RECOVERY_CODES = new Set<string>([
  'TRAINING_ROUND_DUPLICATE',
  'TRAINING_SESSION_COMPLETED',
  'TRAINING_SESSION_NOT_FOUND',
  'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
  'TRAINING_SCENARIO_MISMATCH',
]);

export type TrainingRoundRecoveryReason =
  | 'duplicate'
  | 'completed'
  | 'scenario-mismatch'
  | null;

export const isTrainingRoundSessionLevelRecoveryError = (error: unknown): boolean =>
  isServiceError(error) && SESSION_LEVEL_RECOVERY_CODES.has(error.code);

export const resolveTrainingRoundRecoveryReason = (
  error: unknown
): TrainingRoundRecoveryReason => {
  if (!isServiceError(error)) {
    return null;
  }

  if (error.code === 'TRAINING_ROUND_DUPLICATE') {
    return 'duplicate';
  }

  if (error.code === 'TRAINING_SESSION_COMPLETED') {
    return 'completed';
  }

  if (error.code === 'TRAINING_SCENARIO_MISMATCH') {
    return 'scenario-mismatch';
  }

  return null;
};

export const getTrainingRoundSubmitErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '\u63d0\u4ea4\u8bad\u7ec3\u56de\u5408\u8d85\u65f6\uff0c\u8bf7\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '\u8bad\u7ec3\u63d0\u4ea4\u670d\u52a1\u6682\u65f6\u4e0d\u53ef\u7528\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_COMPLETED') {
    return '\u8bad\u7ec3\u5df2\u5b8c\u6210\uff0c\u8bf7\u67e5\u770b\u8bad\u7ec3\u62a5\u544a\u6216\u91cd\u65b0\u5f00\u59cb\u8bad\u7ec3\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '\u8bad\u7ec3\u4f1a\u8bdd\u4e0d\u5b58\u5728\uff0c\u8bf7\u91cd\u65b0\u5f00\u59cb\u8bad\u7ec3\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '\u8bad\u7ec3\u4f1a\u8bdd\u6062\u590d\u72b6\u6001\u635f\u574f\uff0c\u8bf7\u91cd\u65b0\u5f00\u59cb\u8bad\u7ec3\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SCENARIO_MISMATCH') {
    return '\u5f53\u524d\u63d0\u4ea4\u573a\u666f\u5df2\u8fc7\u671f\uff0c\u9875\u9762\u5c06\u6309\u670d\u52a1\u7aef\u4f1a\u8bdd\u8fdb\u5ea6\u91cd\u65b0\u6062\u590d\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_MEDIA_TASK_INVALID') {
    return '\u5f53\u524d\u56de\u5408\u5305\u542b\u65e0\u6548\u5a92\u4f53\u4efb\u52a1\u914d\u7f6e\uff0c\u8bf7\u8c03\u6574\u540e\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_MEDIA_TASK_CONFLICT') {
    return '\u5f53\u524d\u5a92\u4f53\u4efb\u52a1\u8bf7\u6c42\u4e0e\u5df2\u6709\u5e42\u7b49\u8bb0\u5f55\u51b2\u7a81\uff0c\u8bf7\u66f4\u6362\u53c2\u6570\u540e\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_MEDIA_TASK_UNSUPPORTED') {
    return '\u5f53\u524d\u56de\u5408\u5305\u542b\u6682\u4e0d\u652f\u6301\u7684\u5a92\u4f53\u4efb\u52a1\u7c7b\u578b\uff0c\u8bf7\u8c03\u6574\u540e\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_MEDIA_PROVIDER_UNAVAILABLE') {
    return '\u5a92\u4f53\u751f\u6210\u670d\u52a1\u6682\u4e0d\u53ef\u7528\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_MEDIA_TASK_EXECUTION_FAILED') {
    return '\u5a92\u4f53\u4efb\u52a1\u6267\u884c\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002';
  }

  if (isServiceError(error) && error.code === 'TRAINING_MEDIA_TASK_TIMEOUT') {
    return '\u5a92\u4f53\u4efb\u52a1\u5904\u7406\u8d85\u65f6\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5\u3002';
  }

  return getServiceErrorMessage(error, '\u63d0\u4ea4\u8bad\u7ec3\u56de\u5408\u5931\u8d25\u3002');
};

export const getTrainingRoundNextScenarioErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '\u56de\u5408\u5df2\u63d0\u4ea4\uff0c\u4f46\u4e0b\u4e00\u8bad\u7ec3\u573a\u666f\u52a0\u8f7d\u8d85\u65f6\uff0c\u8bf7\u91cd\u8bd5\u6062\u590d\u5f53\u524d\u8bad\u7ec3\u3002';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '\u56de\u5408\u5df2\u63d0\u4ea4\uff0c\u4f46\u4e0b\u4e00\u8bad\u7ec3\u573a\u666f\u6682\u65f6\u4e0d\u53ef\u7528\uff0c\u8bf7\u91cd\u8bd5\u6062\u590d\u5f53\u524d\u8bad\u7ec3\u3002';
  }

  return getServiceErrorMessage(error, '\u56de\u5408\u5df2\u63d0\u4ea4\uff0c\u4f46\u65e0\u6cd5\u7ee7\u7eed\u52a0\u8f7d\u4e0b\u4e00\u8bad\u7ec3\u573a\u666f\u3002');
};
