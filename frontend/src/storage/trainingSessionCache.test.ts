import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearTrainingResumeTarget,
  persistTrainingResumeTarget,
  readTrainingResumeTarget,
  TRAINING_STORAGE_KEYS,
} from './trainingSessionCache';

interface MockStorage extends Storage {
  dump: () => Record<string, string>;
}

const createMockStorage = (): MockStorage => {
  const store = new Map<string, string>();

  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key)! : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
    dump() {
      return Object.fromEntries(store.entries());
    },
  };
};

describe('trainingSessionCache', () => {
  let local: MockStorage;

  beforeEach(() => {
    local = createMockStorage();
    vi.stubGlobal('localStorage', local);
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-20T09:00:00.000Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('persists a resumable training session target as UX cache only', () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-1',
      trainingMode: 'adaptive',
      characterId: '12',
      status: 'in_progress',
    });

    expect(readTrainingResumeTarget()).toEqual({
      sessionId: 'training-session-1',
      trainingMode: 'adaptive',
      characterId: '12',
      status: 'in_progress',
      timestamp: new Date('2026-03-20T09:00:00.000Z').getTime(),
    });

    expect(local.dump()).toHaveProperty(TRAINING_STORAGE_KEYS.TRAINING_RESUME_TARGET);
  });

  it('ignores corrupted cache payloads instead of treating them as session facts', () => {
    local.setItem(TRAINING_STORAGE_KEYS.TRAINING_RESUME_TARGET, '{bad-json');
    expect(readTrainingResumeTarget()).toBeNull();

    local.setItem(
      TRAINING_STORAGE_KEYS.TRAINING_RESUME_TARGET,
      JSON.stringify({
        sessionId: 'training-session-2',
        trainingMode: 'legacy',
        status: 'completed',
      })
    );

    expect(readTrainingResumeTarget()).toEqual({
      sessionId: 'training-session-2',
      trainingMode: null,
      characterId: null,
      status: 'completed',
      timestamp: null,
    });
  });

  it('clears the cached training resume target explicitly', () => {
    persistTrainingResumeTarget({
      sessionId: 'training-session-3',
      trainingMode: 'guided',
    });

    clearTrainingResumeTarget();

    expect(readTrainingResumeTarget()).toBeNull();
    expect(local.getItem(TRAINING_STORAGE_KEYS.TRAINING_RESUME_TARGET)).toBeNull();
  });
});
