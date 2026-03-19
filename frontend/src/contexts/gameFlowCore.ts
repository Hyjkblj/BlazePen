import { createContext } from 'react';
import * as gameStorage from '@/storage/gameStorage';
import type {
  CharacterData,
  GameMessage,
  GameSave,
  GameSessionSnapshot,
  InitialGameData,
  MainGameSave,
} from '@/types/game';
import { resolvePreferredCharacterId } from '@/utils/gameSession';

export interface RestoreSessionState {
  threadId: string | null;
  characterId: string | null;
}

export interface ActiveSessionState {
  threadId: string | null;
  characterId: string | null;
  initialGameData: InitialGameData | null;
}

export interface RuntimeSessionState {
  restoreSession: RestoreSessionState;
  activeSession: ActiveSessionState;
  currentCharacterId: string | null;
}

export interface GameFlowState {
  characterDraft: CharacterData | null;
  createdCharacterId: string | null;
  runtimeSession: RuntimeSessionState;
}

export interface SetActiveSessionParams {
  threadId: string | null;
  characterId: string | null;
  initialGameData?: InitialGameData | null;
}

export interface PersistGameProgressParams {
  threadId: string;
  messages: GameMessage[];
  characterId?: string;
  snapshot?: GameSessionSnapshot;
}

export interface GameFlowContextValue {
  state: GameFlowState;
  setCharacterDraft: (data: CharacterData | null) => void;
  updateCharacterDraft: (
    updater: (current: CharacterData | null) => CharacterData | null
  ) => void;
  setCreatedCharacterId: (id: string | null) => void;
  setRestoreSession: (threadId: string | null, characterId?: string | null) => void;
  clearRestoreSession: () => void;
  setActiveSession: (params: SetActiveSessionParams) => void;
  clearActiveSession: () => void;
  clearInitialGameData: () => void;
  setCurrentCharacterId: (characterId: string | null) => void;
  getResumeSave: () => MainGameSave | null;
  getThreadSave: (threadId: string) => GameSave | null;
  persistGameProgress: (params: PersistGameProgressParams) => void;
  hydrateFromStorage: () => void;
}

export const readStorageState = (): GameFlowState => {
  const characterDraft = gameStorage.getCharacterData();
  const activeThreadId = gameStorage.getGameThreadId();
  const activeCharacterId = gameStorage.getGameCharacterId();

  return {
    characterDraft,
    createdCharacterId: gameStorage.getCreatedCharacterId(),
    runtimeSession: {
      restoreSession: {
        threadId: gameStorage.getRestoreThreadId(),
        characterId: gameStorage.getRestoreCharacterId(),
      },
      activeSession: {
        threadId: activeThreadId,
        characterId: activeCharacterId,
        initialGameData: gameStorage.getInitialGameData(),
      },
      currentCharacterId: resolvePreferredCharacterId({
        currentCharacterId: gameStorage.getCurrentCharacterId(),
        activeCharacterId,
        draftCharacterId: characterDraft?.characterId,
      }),
    },
  };
};

export const getResumeSave = (): MainGameSave | null => gameStorage.getMainGameSave();

export const getThreadSave = (threadId: string): GameSave | null => gameStorage.getGameSave(threadId);

export const persistCharacterDraft = (data: CharacterData | null): void => {
  if (data) {
    gameStorage.setCharacterData(data);
    return;
  }

  gameStorage.removeCharacterData();
};

export const persistCreatedCharacterId = (id: string | null): void => {
  if (id) {
    gameStorage.setCreatedCharacterId(id);
    return;
  }

  gameStorage.removeCreatedCharacterId();
};

export const persistRestoreSession = (
  threadId: string | null,
  characterId: string | null = null
): void => {
  gameStorage.removeRestoreIds();

  if (threadId) {
    gameStorage.setRestoreThreadId(threadId);
  }

  if (characterId) {
    gameStorage.setRestoreCharacterId(characterId);
  }
};

export const persistActiveSession = ({
  threadId,
  characterId,
  initialGameData = null,
}: SetActiveSessionParams): void => {
  if (threadId && characterId) {
    gameStorage.setGameIds(threadId, characterId);
  } else {
    gameStorage.clearGameIds();
  }

  if (initialGameData) {
    gameStorage.setInitialGameData(initialGameData);
  } else {
    gameStorage.clearInitialGameData();
  }

  if (characterId) {
    gameStorage.setCurrentCharacterId(characterId);
  }
};

export const clearPersistedInitialGameData = (): void => {
  gameStorage.clearInitialGameData();
};

export const persistCurrentCharacterId = (characterId: string | null): void => {
  if (characterId) {
    gameStorage.setCurrentCharacterId(characterId);
    return;
  }

  gameStorage.clearCurrentCharacterId();
};

export const persistGameProgress = ({
  threadId,
  messages,
  characterId,
  snapshot,
}: PersistGameProgressParams): void => {
  const timestamp = Date.now();
  const lastMessage = messages.length > 0 ? messages[messages.length - 1].content : undefined;

  gameStorage.setGameSave({
    threadId,
    characterId,
    messages,
    lastMessage,
    snapshot,
    timestamp,
  });

  gameStorage.setMainGameSave({
    threadId,
    characterId,
    lastMessage,
    snapshot,
    timestamp,
  });
};

export const GameFlowContext = createContext<GameFlowContextValue | null>(null);
