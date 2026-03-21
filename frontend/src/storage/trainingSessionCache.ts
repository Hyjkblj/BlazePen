import type { TrainingMode } from '@/types/training';

const TRAINING_RESUME_TARGET_KEY = 'trainingResumeTarget';

export interface TrainingResumeTarget {
  sessionId: string;
  trainingMode: TrainingMode | null;
  characterId: string | null;
  status: string | null;
  timestamp: number | null;
}

export interface PersistTrainingResumeTargetParams {
  sessionId: string;
  trainingMode?: TrainingMode | null;
  characterId?: string | null;
  status?: string | null;
  timestamp?: number;
}

const normalizeStoredString = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  if (normalized === '' || normalized === 'null' || normalized === 'undefined') {
    return null;
  }

  return normalized;
};

const normalizeStoredTrainingMode = (value: unknown): TrainingMode | null => {
  switch (normalizeStoredString(value)) {
    case 'guided':
      return 'guided';
    case 'self-paced':
      return 'self-paced';
    case 'adaptive':
      return 'adaptive';
    default:
      return null;
  }
};

const parseResumeTarget = (raw: string | null): TrainingResumeTarget | null => {
  if (!raw) {
    return null;
  }

  try {
    const payload = JSON.parse(raw) as Record<string, unknown>;
    const sessionId = normalizeStoredString(payload.sessionId);
    if (!sessionId) {
      return null;
    }

    return {
      sessionId,
      trainingMode: normalizeStoredTrainingMode(payload.trainingMode),
      characterId: normalizeStoredString(payload.characterId),
      status: normalizeStoredString(payload.status),
      timestamp:
        typeof payload.timestamp === 'number' && Number.isFinite(payload.timestamp)
          ? payload.timestamp
          : null,
    };
  } catch {
    return null;
  }
};

export const readTrainingResumeTarget = (): TrainingResumeTarget | null =>
  parseResumeTarget(localStorage.getItem(TRAINING_RESUME_TARGET_KEY));

export const persistTrainingResumeTarget = ({
  sessionId,
  trainingMode = null,
  characterId = null,
  status = null,
  timestamp = Date.now(),
}: PersistTrainingResumeTargetParams): void => {
  const normalizedSessionId = normalizeStoredString(sessionId);
  if (!normalizedSessionId) {
    localStorage.removeItem(TRAINING_RESUME_TARGET_KEY);
    return;
  }

  localStorage.setItem(
    TRAINING_RESUME_TARGET_KEY,
    JSON.stringify({
      sessionId: normalizedSessionId,
      trainingMode: trainingMode ?? null,
      characterId: normalizeStoredString(characterId),
      status: normalizeStoredString(status),
      timestamp,
    })
  );
};

export const clearTrainingResumeTarget = (): void => {
  localStorage.removeItem(TRAINING_RESUME_TARGET_KEY);
};

export const TRAINING_STORAGE_KEYS = {
  TRAINING_RESUME_TARGET: TRAINING_RESUME_TARGET_KEY,
} as const;
