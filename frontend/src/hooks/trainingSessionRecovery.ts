import type { ActiveTrainingSessionState } from '@/contexts';
import { isServiceError } from '@/services/serviceError';
import {
  clearTrainingResumeTarget,
  readTrainingResumeTarget,
} from '@/storage/trainingSessionCache';

export const isTerminalTrainingSessionRecoveryError = (error: unknown): boolean =>
  isServiceError(error) &&
  (error.code === 'TRAINING_SESSION_NOT_FOUND' ||
    error.code === 'TRAINING_SESSION_RECOVERY_STATE_CORRUPTED');

export interface ClearTrainingSessionRecoveryArtifactsParams {
  invalidSessionId: string | null | undefined;
  activeSession: ActiveTrainingSessionState | null;
  clearActiveSession: () => void;
}

const normalizeSessionId = (value: string | null | undefined): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

export const clearTrainingSessionRecoveryArtifacts = ({
  invalidSessionId,
  activeSession,
  clearActiveSession,
}: ClearTrainingSessionRecoveryArtifactsParams): boolean => {
  const normalizedInvalidSessionId = normalizeSessionId(invalidSessionId);
  if (!normalizedInvalidSessionId) {
    return false;
  }

  let cleared = false;

  if (normalizeSessionId(activeSession?.sessionId ?? null) === normalizedInvalidSessionId) {
    clearActiveSession();
    cleared = true;
  }

  const resumeTarget = readTrainingResumeTarget();
  if (normalizeSessionId(resumeTarget?.sessionId ?? null) === normalizedInvalidSessionId) {
    clearTrainingResumeTarget();
    cleared = true;
  }

  return cleared;
};
