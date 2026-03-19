import type { GameMessage, GameSave, GameSessionSnapshot, MainGameSave } from '@/types/game';
import { getGameSave, getMainGameSave, setGameSave, setMainGameSave } from './gameStorage';

export interface PersistStoryProgressParams {
  threadId: string;
  messages: GameMessage[];
  characterId?: string;
  snapshot?: GameSessionSnapshot;
}

export const readStoryResumeSave = (): MainGameSave | null => getMainGameSave();

export const readStoryThreadSave = (threadId: string): GameSave | null => getGameSave(threadId);

export const persistStoryProgress = ({
  threadId,
  messages,
  characterId,
  snapshot,
}: PersistStoryProgressParams): void => {
  const timestamp = Date.now();
  const lastMessage = messages.length > 0 ? messages[messages.length - 1].content : undefined;

  setGameSave({
    threadId,
    characterId,
    messages,
    lastMessage,
    snapshot,
    timestamp,
  });

  setMainGameSave({
    threadId,
    characterId,
    lastMessage,
    snapshot,
    timestamp,
  });
};
