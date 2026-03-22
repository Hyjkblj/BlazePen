import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import { isTerminalTrainingSessionRecoveryError } from './trainingSessionRecovery';

export interface TrainingReadFailureState {
  errorCode: string | null;
  errorMessage: string;
  shouldClearData: boolean;
  shouldClearRecoveryArtifacts: boolean;
}

export const getTrainingReadErrorMessage = (
  error: unknown,
  fallbackMessage: string
): string => {
  if (isServiceError(error) && error.code === 'TRAINING_SESSION_NOT_FOUND') {
    return '训练会话不存在，请返回训练主页重新开始。';
  }

  if (isServiceError(error) && error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED') {
    return '训练会话恢复状态损坏，当前结果无法读取。';
  }

  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '训练结果读取超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return '训练结果服务暂时不可用，请稍后重试。';
  }

  return getServiceErrorMessage(error, fallbackMessage);
};

export const resolveTrainingReadFailureState = ({
  error,
  fallbackMessage,
  hasCurrentSessionData,
}: {
  error: unknown;
  fallbackMessage: string;
  hasCurrentSessionData: boolean;
}): TrainingReadFailureState => {
  const isTerminalRecoveryError = isTerminalTrainingSessionRecoveryError(error);

  return {
    errorCode: isServiceError(error) ? error.code : null,
    errorMessage: getTrainingReadErrorMessage(error, fallbackMessage),
    shouldClearData: isTerminalRecoveryError || !hasCurrentSessionData,
    shouldClearRecoveryArtifacts: isTerminalRecoveryError,
  };
};
