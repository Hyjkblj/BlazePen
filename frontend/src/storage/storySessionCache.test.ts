import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  persistStoryProgress,
  readStoryResumeTarget,
  readStoryResumeSave,
  readStoryThreadSave,
} from './storySessionCache';
import { GAME_STORAGE_KEYS } from './gameStorage';

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

describe('storySessionCache', () => {
  let session: MockStorage;
  let local: MockStorage;

  beforeEach(() => {
    session = createMockStorage();
    local = createMockStorage();
    vi.stubGlobal('sessionStorage', session);
    vi.stubGlobal('localStorage', local);
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-03-19T20:00:00.000Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('persists story progress into both the thread save and resume save buckets', () => {
    persistStoryProgress({
      threadId: 'thread-1',
      characterId: 'character-1',
      messages: [
        { role: 'assistant', content: 'Intro' },
        { role: 'user', content: 'Choose option 1' },
      ],
      snapshot: {
        currentDialogue: 'Intro',
        currentOptions: [{ id: 1, text: 'Choose option 1', type: 'action' }],
        currentScene: 'study_room',
        sceneImageUrl: '/scene.png',
        characterImageUrl: '/character.png',
        compositeImageUrl: null,
        shouldUseComposite: false,
        isGameFinished: false,
      },
    });

    expect(readStoryThreadSave('thread-1')).toEqual({
      threadId: 'thread-1',
      characterId: 'character-1',
      messages: [
        { role: 'assistant', content: 'Intro' },
        { role: 'user', content: 'Choose option 1' },
      ],
      lastMessage: 'Choose option 1',
      snapshot: {
        currentDialogue: 'Intro',
        currentOptions: [{ id: 1, text: 'Choose option 1', type: 'action' }],
        currentScene: 'study_room',
        sceneImageUrl: '/scene.png',
        characterImageUrl: '/character.png',
        compositeImageUrl: null,
        shouldUseComposite: false,
        isGameFinished: false,
      },
      timestamp: new Date('2026-03-19T20:00:00.000Z').getTime(),
    });

    expect(readStoryResumeSave()).toEqual({
      threadId: 'thread-1',
      characterId: 'character-1',
      lastMessage: 'Choose option 1',
      snapshot: {
        currentDialogue: 'Intro',
        currentOptions: [{ id: 1, text: 'Choose option 1', type: 'action' }],
        currentScene: 'study_room',
        sceneImageUrl: '/scene.png',
        characterImageUrl: '/character.png',
        compositeImageUrl: null,
        shouldUseComposite: false,
        isGameFinished: false,
      },
      timestamp: new Date('2026-03-19T20:00:00.000Z').getTime(),
    });
  });

  it('returns null when the requested thread save does not exist', () => {
    expect(readStoryThreadSave('missing-thread')).toBeNull();
    expect(readStoryResumeSave()).toBeNull();
  });

  it('prefers the active story session over the local resume save when resolving a continue target', () => {
    session.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-active');
    session.setItem(GAME_STORAGE_KEYS.GAME_CHARACTER_ID, 'character-active');
    local.setItem(
      GAME_STORAGE_KEYS.MAIN_SAVE,
      JSON.stringify({
        threadId: 'thread-saved',
        characterId: 'character-saved',
        timestamp: 1,
      })
    );

    expect(readStoryResumeTarget()).toEqual({
      threadId: 'thread-active',
      characterId: 'character-active',
      source: 'active-session',
    });
  });

  it('fills a missing active-session character id from the matching resume save', () => {
    session.setItem(GAME_STORAGE_KEYS.GAME_THREAD_ID, 'thread-active');
    local.setItem(
      GAME_STORAGE_KEYS.MAIN_SAVE,
      JSON.stringify({
        threadId: 'thread-active',
        characterId: 'character-saved',
        timestamp: 1,
      })
    );

    expect(readStoryResumeTarget()).toEqual({
      threadId: 'thread-active',
      characterId: 'character-saved',
      source: 'active-session',
    });
  });

  it('falls back to the durable resume save when no active session exists', () => {
    local.setItem(
      GAME_STORAGE_KEYS.MAIN_SAVE,
      JSON.stringify({
        threadId: 'thread-saved',
        characterId: 'character-saved',
        timestamp: 1,
      })
    );

    expect(readStoryResumeTarget()).toEqual({
      threadId: 'thread-saved',
      characterId: 'character-saved',
      source: 'resume-save',
    });
  });
});
