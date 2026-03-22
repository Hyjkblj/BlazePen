import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import { isTerminalTrainingSessionRecoveryError } from './trainingSessionRecovery';

export interface TrainingRestoreFailureState {
  errorMessage: string;
  shouldClearRecoveryArtifacts: boolean;
}

export const getTrainingRestoreErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '训练会话不存在，已清理本地恢复入口。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '训练会话恢复状态损坏，已清理本地恢复入口。';
  }

  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '训练恢复超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练恢复服务暂时不可用，请稍后重试。';
  }

  return getServiceErrorMessage(error, '恢复训练会话失败。');
};

export const getTrainingStartErrorMessage = (error: unknown): string => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '训练初始化超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练初始化服务暂时不可用，请稍后重试。';
  }

  return getServiceErrorMessage(error, '启动训练失败。');
};

export const resolveTrainingRestoreFailureState = (
  error: unknown
): TrainingRestoreFailureState => ({
  errorMessage: getTrainingRestoreErrorMessage(error),
  shouldClearRecoveryArtifacts: isTerminalTrainingSessionRecoveryError(error),
});
