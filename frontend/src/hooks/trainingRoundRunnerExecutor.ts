import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';

const SESSION_LEVEL_RECOVERY_CODES = new Set<string>([
  'TRAINING_ROUND_DUPLICATE',
  'TRAINING_SESSION_COMPLETED',
  'TRAINING_SESSION_NOT_FOUND',
  'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED',
]);

export type TrainingRoundRecoveryReason = 'duplicate' | 'completed' | null;

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

  return null;
};

export const getTrainingRoundSubmitErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '提交训练回合超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练提交服务暂时不可用，请稍后重试。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_COMPLETED') {
    return '训练已完成，请查看训练报告或重新开始训练。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '训练会话不存在，请重新开始训练。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '训练会话恢复状态损坏，请重新开始训练。';
  }

  return getServiceErrorMessage(error, '提交训练回合失败。');
};

export const getTrainingRoundNextScenarioErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '回合已提交，但下一训练场景加载超时，请重试恢复当前训练。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '回合已提交，但下一训练场景暂时不可用，请重试恢复当前训练。';
  }

  return getServiceErrorMessage(error, '回合已提交，但无法继续加载下一训练场景。');
};
