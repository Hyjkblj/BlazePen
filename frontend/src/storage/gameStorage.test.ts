import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  GAME_STORAGE_KEYS,
  getCurrentCharacterId,
  getGameCharacterId,
  getGameSave,
  getGameThreadId,
  getMainGameSave,
  getRestoreCharacterId,
  getRestoreThreadId,
  setCurrentCharacterId,
  setGameIds,
} from './gameStorage';

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

describe('gameStorage string normalization', () => {
  let session: MockStorage;
  let local: MockStorage;

  beforeEach(() => {
    session = createMockStorage();
    local = createMockStorage();
    vi.stubGlobal('sessionStorage', session);
    vi.stubGlobal('localStorage', local);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sanitizes dirty session string reads', () => {
    session.setItem(GAME_STORAGE_KEYS.RESTORE_THREAD_ID, ' null ');
    session.setItem(GAME_STORAGE_KEYS.RESTORE_CHARACTER_ID, 'undefined');
    session.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, ' thread-123 ');
    session.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, ' character-456 ');
    session.setItem(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID, '  ');

    expect(getRestoreThreadId()).toBeNull();
    expect(getRestoreCharacterId()).toBeNull();
    expect(getGameThreadId()).toBe('thread-123');
    expect(getGameCharacterId()).toBe('character-456');
    expect(getCurrentCharacterId()).toBeNull();
  });

  it('refuses to persist invalid game ids and clears invalid current ids', () => {
    setGameIds('null', 'character-1');
    expect(session.dump()).not.toHaveProperty(GAME_STORAGE_KEYS.GAME_THREAD_ID);
    expect(session.dump()).not.toHaveProperty(GAME_STORAGE_KEYS.GAME_CHARACTER_ID);

    setCurrentCharacterId('undefined');
    expect(session.dump()).not.toHaveProperty(GAME_STORAGE_KEYS.CURRENT_CHARACTER_ID);
  });

  it('sanitizes persisted save identifiers on read', () => {
    local.setItem(
      'gameSave_thread-1',
      JSON.stringify({
        threadId: 'thread-1',
        characterId: ' null ',
        messages: [],
        timestamp: 1,
      })
    );
    local.setItem(
      GAME_STORAGE_KEYS.MAIN_SAVE,
      JSON.stringify({
        threadId: ' thread-1 ',
        characterId: ' undefined ',
        timestamp: 1,
      })
    );

    expect(getGameSave('thread-1')).toEqual({
      threadId: 'thread-1',
      characterId: undefined,
      messages: [],
      timestamp: 1,
    });
    expect(getMainGameSave()).toEqual({
      threadId: 'thread-1',
      characterId: undefined,
      timestamp: 1,
    });
  });
});
