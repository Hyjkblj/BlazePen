/**
 * 游戏相关 sessionStorage / localStorage 统一封装
 * 键名与解析集中在此，避免各页面手写 key 与 JSON 解析
 */
import type { CharacterData, GameSave, MainGameSave, InitialGameData } from '@/types/game';

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
  return sessionStorage.getItem(KEYS.CREATED_CHARACTER_ID);
}

export function setCreatedCharacterId(id: string): void {
  sessionStorage.setItem(KEYS.CREATED_CHARACTER_ID, id);
}

export function removeCreatedCharacterId(): void {
  sessionStorage.removeItem(KEYS.CREATED_CHARACTER_ID);
}

export function getRestoreThreadId(): string | null {
  return sessionStorage.getItem(KEYS.RESTORE_THREAD_ID);
}

export function setRestoreThreadId(threadId: string): void {
  sessionStorage.setItem(KEYS.RESTORE_THREAD_ID, threadId);
}

export function getRestoreCharacterId(): string | null {
  return sessionStorage.getItem(KEYS.RESTORE_CHARACTER_ID);
}

export function setRestoreCharacterId(characterId: string): void {
  sessionStorage.setItem(KEYS.RESTORE_CHARACTER_ID, characterId);
}

export function removeRestoreIds(): void {
  sessionStorage.removeItem(KEYS.RESTORE_THREAD_ID);
  sessionStorage.removeItem(KEYS.RESTORE_CHARACTER_ID);
}

export function getGameThreadId(): string | null {
  return sessionStorage.getItem(KEYS.GAME_THREAD_ID);
}

export function getGameCharacterId(): string | null {
  return sessionStorage.getItem(KEYS.GAME_CHARACTER_ID);
}

export function setGameIds(threadId: string, characterId: string): void {
  sessionStorage.setItem(KEYS.GAME_THREAD_ID, threadId);
  sessionStorage.setItem(KEYS.GAME_CHARACTER_ID, characterId);
}

export function clearGameIds(): void {
  sessionStorage.removeItem(KEYS.GAME_THREAD_ID);
  sessionStorage.removeItem(KEYS.GAME_CHARACTER_ID);
}

export function removeGameThreadId(): void {
  sessionStorage.removeItem(KEYS.GAME_THREAD_ID);
}

export function getCurrentCharacterId(): string | null {
  return sessionStorage.getItem(KEYS.CURRENT_CHARACTER_ID);
}

export function setCurrentCharacterId(characterId: string): void {
  sessionStorage.setItem(KEYS.CURRENT_CHARACTER_ID, characterId);
}

export function clearCurrentCharacterId(): void {
  sessionStorage.removeItem(KEYS.CURRENT_CHARACTER_ID);
}

export function getInitialGameData(): InitialGameData | null {
  const raw = sessionStorage.getItem(KEYS.INITIAL_GAME_DATA);
  return parseJson<InitialGameData | null>(raw, null);
}

export function clearInitialGameData(): void {
  sessionStorage.removeItem(KEYS.INITIAL_GAME_DATA);
}

export function setInitialGameData(data: InitialGameData): void {
  sessionStorage.setItem(KEYS.INITIAL_GAME_DATA, JSON.stringify(data));
}

// ---------- localStorage ----------

export function getGameSave(threadId: string): GameSave | null {
  const raw = localStorage.getItem(gameSaveKey(threadId));
  return parseJson<GameSave | null>(raw, null);
}

export function setGameSave(save: GameSave): void {
  localStorage.setItem(gameSaveKey(save.threadId), JSON.stringify(save));
}

export function getMainGameSave(): MainGameSave | null {
  const raw = localStorage.getItem(KEYS.MAIN_SAVE);
  return parseJson<MainGameSave | null>(raw, null);
}

export function setMainGameSave(save: MainGameSave): void {
  localStorage.setItem(KEYS.MAIN_SAVE, JSON.stringify(save));
}

export { KEYS as GAME_STORAGE_KEYS };
