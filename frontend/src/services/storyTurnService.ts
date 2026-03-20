import { processGameInput } from '@/services/gameApi';
import type { GameTurnResult } from '@/types/game';

export interface SubmitStoryTurnParams {
  threadId: string;
  userInput: string;
  characterId: string | null;
}

export const submitStoryTurn = async ({
  threadId,
  userInput,
  characterId,
}: SubmitStoryTurnParams): Promise<GameTurnResult> =>
  processGameInput({
    threadId,
    userInput,
    characterId: characterId ?? undefined,
  });
