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

/** sessionStorage：本会话内场景图批量预创建计划（MainHome 开局后写入） */
const TRAINING_PREWARM_PLAN_KEY = 'trainingPrewarmPlan';

export interface TrainingPrewarmScenarioOutline {
  id: string;
  title: string;
}

export interface TrainingPrewarmPlan {
  sessionId: string;
  scenarios: TrainingPrewarmScenarioOutline[];
}

export const persistTrainingPrewarmPlan = (plan: TrainingPrewarmPlan): void => {
  const sessionId = normalizeStoredString(plan.sessionId);
  if (!sessionId || !Array.isArray(plan.scenarios) || plan.scenarios.length === 0) {
    sessionStorage.removeItem(TRAINING_PREWARM_PLAN_KEY);
    return;
  }
  const scenarios = plan.scenarios
    .map((item) => ({
      id: normalizeStoredString(item.id) ?? '',
      title: normalizeStoredString(item.title) ?? '',
    }))
    .filter((item) => item.id !== '');
  if (!scenarios.length) {
    sessionStorage.removeItem(TRAINING_PREWARM_PLAN_KEY);
    return;
  }
  sessionStorage.setItem(TRAINING_PREWARM_PLAN_KEY, JSON.stringify({ sessionId, scenarios }));
};

export const readTrainingPrewarmPlan = (): TrainingPrewarmPlan | null => {
  try {
    const raw = sessionStorage.getItem(TRAINING_PREWARM_PLAN_KEY);
    if (!raw) return null;
    const payload = JSON.parse(raw) as Record<string, unknown>;
    const sessionId = normalizeStoredString(payload.sessionId);
    if (!sessionId) return null;
    const list = Array.isArray(payload.scenarios) ? payload.scenarios : [];
    const scenarios = list
      .map((item) => {
        if (!item || typeof item !== 'object') return null;
        const rec = item as Record<string, unknown>;
        const id = normalizeStoredString(rec.id);
        if (!id) return null;
        return { id, title: normalizeStoredString(rec.title) ?? id };
      })
      .filter((item): item is TrainingPrewarmScenarioOutline => item !== null);
    if (!scenarios.length) return null;
    return { sessionId, scenarios };
  } catch {
    return null;
  }
};

export const clearTrainingPrewarmPlan = (): void => {
  sessionStorage.removeItem(TRAINING_PREWARM_PLAN_KEY);
};
