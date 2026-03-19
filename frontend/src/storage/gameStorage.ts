/**
 * 游戏相关 sessionStorage / localStorage 统一封装
 * 键名与解析集中在此，避免各页面手写 key 与 JSON 解析
 */
import type { CharacterData, GameSave, MainGameSave, InitialGameData } from '@/types/game';
import { normalizeInitialGameData } from '@/utils/storyScene';

const KEYS = {
  CHARACTER_DATA: 'characterData',
  CREATED_CHARACTER_ID: 'createdCharacterId',
  RESTORE_THREAD_ID: 'restoreThreadId',
  RESTORE_CHARACTER_ID: 'restoreCharacterId',
  GAME_THREAD_ID: 'gameThreadId',
  GAME_CHARACTER_ID: 'gameCharacterId',
  CURRENT_CHARACTER_ID: 'currentCharacterId',
  INITIAL_GAME_DATA: 'initialGameData',
  MAIN_SAVE: 'gameSave',
} as const;

const gameSaveKey = (threadId: string) => `gameSave_${threadId}`;

function parseJson<T>(raw: string | null, fallback: T): T {
  if (raw == null || raw === '') return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function normalizeStoredString(raw: string | null | undefined): string | null {
  if (typeof raw !== 'string') {
    return null;
  }

  const normalized = raw.trim();
  if (normalized === '' || normalized === 'null' || normalized === 'undefined') {
    return null;
  }

  return normalized;
}

function getSessionString(key: string): string | null {
  return normalizeStoredString(sessionStorage.getItem(key));
}

function setSessionString(key: string, value: string): void {
  const normalized = normalizeStoredString(value);

  if (!normalized) {
    sessionStorage.removeItem(key);
    return;
  }

  sessionStorage.setItem(key, normalized);
}

// ---------- sessionStorage ----------

export function getCharacterData(): CharacterData | null {
  const raw = sessionStorage.getItem(KEYS.CHARACTER_DATA);
  return parseJson<CharacterData | null>(raw, null);
}

export function setCharacterData(data: CharacterData): void {
  sessionStorage.setItem(KEYS.CHARACTER_DATA, JSON.stringify(data));
}

export function removeCharacterData(): void {
  sessionStorage.removeItem(KEYS.CHARACTER_DATA);
}

export function getCreatedCharacterId(): string | null {
  return getSessionString(KEYS.CREATED_CHARACTER_ID);
}

export function setCreatedCharacterId(id: string): void {
  setSessionString(KEYS.CREATED_CHARACTER_ID, id);
}

export function removeCreatedCharacterId(): void {
  sessionStorage.removeItem(KEYS.CREATED_CHARACTER_ID);
}

export function getRestoreThreadId(): string | null {
  return getSessionString(KEYS.RESTORE_THREAD_ID);
}

export function setRestoreThreadId(threadId: string): void {
  setSessionString(KEYS.RESTORE_THREAD_ID, threadId);
}

export function getRestoreCharacterId(): string | null {
  return getSessionString(KEYS.RESTORE_CHARACTER_ID);
}

export function setRestoreCharacterId(characterId: string): void {
  setSessionString(KEYS.RESTORE_CHARACTER_ID, characterId);
}

export function removeRestoreIds(): void {
  sessionStorage.removeItem(KEYS.RESTORE_THREAD_ID);
  sessionStorage.removeItem(KEYS.RESTORE_CHARACTER_ID);
}

export function getGameThreadId(): string | null {
  return getSessionString(KEYS.GAME_THREAD_ID);
}

export function getGameCharacterId(): string | null {
  return getSessionString(KEYS.GAME_CHARACTER_ID);
}

export function setGameIds(threadId: string, characterId: string): void {
  const normalizedThreadId = normalizeStoredString(threadId);
  const normalizedCharacterId = normalizeStoredString(characterId);

  if (!normalizedThreadId || !normalizedCharacterId) {
    clearGameIds();
    return;
  }

  sessionStorage.setItem(KEYS.GAME_THREAD_ID, normalizedThreadId);
  sessionStorage.setItem(KEYS.GAME_CHARACTER_ID, normalizedCharacterId);
}

export function clearGameIds(): void {
  sessionStorage.removeItem(KEYS.GAME_THREAD_ID);
  sessionStorage.removeItem(KEYS.GAME_CHARACTER_ID);
}

export function removeGameThreadId(): void {
  sessionStorage.removeItem(KEYS.GAME_THREAD_ID);
}

export function getCurrentCharacterId(): string | null {
  return getSessionString(KEYS.CURRENT_CHARACTER_ID);
}

export function setCurrentCharacterId(characterId: string): void {
  setSessionString(KEYS.CURRENT_CHARACTER_ID, characterId);
}

export function clearCurrentCharacterId(): void {
  sessionStorage.removeItem(KEYS.CURRENT_CHARACTER_ID);
}

export function getInitialGameData(): InitialGameData | null {
  const raw = sessionStorage.getItem(KEYS.INITIAL_GAME_DATA);
  return normalizeInitialGameData(parseJson<InitialGameData | null>(raw, null));
}

export function clearInitialGameData(): void {
  sessionStorage.removeItem(KEYS.INITIAL_GAME_DATA);
}

export function setInitialGameData(data: InitialGameData): void {
  sessionStorage.setItem(KEYS.INITIAL_GAME_DATA, JSON.stringify(data));
}

// ---------- localStorage ----------

export function getGameSave(threadId: string): GameSave | null {
  const normalizedThreadId = normalizeStoredString(threadId);
  if (!normalizedThreadId) {
    return null;
  }

  const raw = localStorage.getItem(gameSaveKey(normalizedThreadId));
  const save = parseJson<GameSave | null>(raw, null);

  if (!save) {
    return null;
  }

  return {
    ...save,
    threadId: normalizeStoredString(save.threadId) ?? normalizedThreadId,
    characterId: normalizeStoredString(save.characterId) ?? undefined,
  };
}

export function setGameSave(save: GameSave): void {
  const normalizedThreadId = normalizeStoredString(save.threadId);
  if (!normalizedThreadId) {
    return;
  }

  localStorage.setItem(
    gameSaveKey(normalizedThreadId),
    JSON.stringify({
      ...save,
      threadId: normalizedThreadId,
      characterId: normalizeStoredString(save.characterId) ?? undefined,
    })
  );
}

export function getMainGameSave(): MainGameSave | null {
  const raw = localStorage.getItem(KEYS.MAIN_SAVE);
  const save = parseJson<MainGameSave | null>(raw, null);

  if (!save) {
    return null;
  }

  const normalizedThreadId = normalizeStoredString(save.threadId);
  if (!normalizedThreadId) {
    return null;
  }

  return {
    ...save,
    threadId: normalizedThreadId,
    characterId: normalizeStoredString(save.characterId) ?? undefined,
  };
}

export function setMainGameSave(save: MainGameSave): void {
  const normalizedThreadId = normalizeStoredString(save.threadId);
  if (!normalizedThreadId) {
    return;
  }

  localStorage.setItem(
    KEYS.MAIN_SAVE,
    JSON.stringify({
      ...save,
      threadId: normalizedThreadId,
      characterId: normalizeStoredString(save.characterId) ?? undefined,
    })
  );
}

export { KEYS as GAME_STORAGE_KEYS };
