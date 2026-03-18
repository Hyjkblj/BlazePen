import { createContext } from 'react';
import * as gameStorage from '@/storage/gameStorage';
import type { CharacterData, InitialGameData } from '@/types/game';

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
      currentCharacterId:
        gameStorage.getCurrentCharacterId() || activeCharacterId || characterDraft?.characterId || null,
    },
  };
};

export const GameFlowContext = createContext<GameFlowContextValue | null>(null);
