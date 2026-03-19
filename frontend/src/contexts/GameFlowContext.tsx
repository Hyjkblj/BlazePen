import { useReducer, type ReactNode } from 'react';
import type { CharacterData } from '@/types/game';
import {
  clearPersistedInitialGameData,
  GameFlowContext,
  persistActiveSession as persistSessionState,
  persistCharacterDraft,
  persistCreatedCharacterId,
  persistCurrentCharacterId,
  persistRestoreSession,
  readStorageState,
  type ActiveSessionState,
  type GameFlowState,
  type SetActiveSessionParams,
} from './gameFlowCore';

type GameFlowAction =
  | { type: 'set-character-draft'; payload: CharacterData | null }
  | { type: 'set-created-character-id'; payload: string | null }
  | { type: 'set-restore-session'; payload: GameFlowState['runtimeSession']['restoreSession'] }
  | { type: 'set-active-session'; payload: ActiveSessionState }
  | { type: 'set-current-character-id'; payload: string | null };

const reducer = (state: GameFlowState, action: GameFlowAction): GameFlowState => {
  switch (action.type) {
    case 'set-character-draft':
      return {
        ...state,
        characterDraft: action.payload,
      };
    case 'set-created-character-id':
      return {
        ...state,
        createdCharacterId: action.payload,
      };
    case 'set-restore-session':
      return {
        ...state,
        runtimeSession: {
          ...state.runtimeSession,
          restoreSession: action.payload,
        },
      };
    case 'set-active-session':
      return {
        ...state,
        runtimeSession: {
          ...state.runtimeSession,
          activeSession: action.payload,
          currentCharacterId: action.payload.characterId || state.runtimeSession.currentCharacterId,
        },
      };
    case 'set-current-character-id':
      return {
        ...state,
        runtimeSession: {
          ...state.runtimeSession,
          currentCharacterId: action.payload,
        },
      };
    default:
      return state;
  }
};

export function GameFlowProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, readStorageState);

  const setCharacterDraft = (data: CharacterData | null) => {
    persistCharacterDraft(data);

    dispatch({ type: 'set-character-draft', payload: data });

    if (data?.characterId) {
      persistCurrentCharacterId(data.characterId);
      dispatch({ type: 'set-current-character-id', payload: data.characterId });
    } else if (!state.runtimeSession.activeSession.characterId) {
      persistCurrentCharacterId(null);
      dispatch({ type: 'set-current-character-id', payload: null });
    }
  };

  const updateCharacterDraft = (
    updater: (current: CharacterData | null) => CharacterData | null
  ) => {
    const nextDraft = updater(state.characterDraft);
    setCharacterDraft(nextDraft);
  };

  const setCreatedCharacterId = (id: string | null) => {
    persistCreatedCharacterId(id);
    dispatch({ type: 'set-created-character-id', payload: id });
  };

  const setRestoreSession = (threadId: string | null, characterId: string | null = null) => {
    persistRestoreSession(threadId, characterId);

    dispatch({
      type: 'set-restore-session',
      payload: { threadId, characterId },
    });
  };

  const clearRestoreSession = () => {
    setRestoreSession(null, null);
  };

  const setActiveSession = ({
    threadId,
    characterId,
    initialGameData = null,
  }: SetActiveSessionParams) => {
    persistSessionState({ threadId, characterId, initialGameData });

    dispatch({
      type: 'set-active-session',
      payload: {
        threadId,
        characterId,
        initialGameData,
      },
    });
  };

  const clearActiveSession = () => {
    setActiveSession({ threadId: null, characterId: null, initialGameData: null });
  };

  const clearInitialGameData = () => {
    clearPersistedInitialGameData();
    dispatch({
      type: 'set-active-session',
      payload: {
        ...state.runtimeSession.activeSession,
        initialGameData: null,
      },
    });
  };

  const setCurrentCharacterId = (characterId: string | null) => {
    persistCurrentCharacterId(characterId);
    dispatch({ type: 'set-current-character-id', payload: characterId });
  };

  return (
    <GameFlowContext.Provider
      value={{
        state,
        setCharacterDraft,
        updateCharacterDraft,
        setCreatedCharacterId,
        setRestoreSession,
        clearRestoreSession,
        setActiveSession,
        clearActiveSession,
        clearInitialGameData,
        setCurrentCharacterId,
      }}
    >
      {children}
    </GameFlowContext.Provider>
  );
}
