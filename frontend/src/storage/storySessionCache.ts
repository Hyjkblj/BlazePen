import type { GameMessage, GameSave, GameSessionSnapshot, MainGameSave } from '@/types/game';
import {
  getGameCharacterId,
  getGameSave,
  getGameThreadId,
  getMainGameSave,
  setGameSave,
  setMainGameSave,
} from './gameStorage';

export interface PersistStoryProgressParams {
  threadId: string;
  messages: GameMessage[];
  characterId?: string;
  snapshot?: GameSessionSnapshot;
}

export interface StoryResumeTarget {
  threadId: string;
  characterId?: string;
  source: 'active-session' | 'resume-save';
}

export const readStoryResumeSave = (): MainGameSave | null => getMainGameSave();

export const readStoryThreadSave = (threadId: string): GameSave | null => getGameSave(threadId);

export const readStoryResumeTarget = (): StoryResumeTarget | null => {
  const resumeSave = getMainGameSave();
  const activeThreadId = getGameThreadId();
  const activeCharacterId = getGameCharacterId();

  if (activeThreadId) {
    return {
      threadId: activeThreadId,
      characterId:
        activeCharacterId ?? (resumeSave?.threadId === activeThreadId ? resumeSave.characterId : undefined),
      source: 'active-session',
    };
  }

  if (!resumeSave?.threadId) {
    return null;
  }

  return {
    threadId: resumeSave.threadId,
    characterId: resumeSave.characterId,
    source: 'resume-save',
  };
};

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
