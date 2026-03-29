import { useCallback, useMemo, useState } from 'react';
import type { GameMessage } from '@/types/game';

const ROLE_LABELS: Record<GameMessage['role'], string> = {
  assistant: '故事内容',
  user: '你的选择',
};

export interface StoryTranscriptEntry {
  id: string;
  role: GameMessage['role'];
  roleLabel: string;
  content: string;
  sequenceNo: number;
}

export interface UseStorySessionTranscriptOptions {
  messages: GameMessage[];
}

export interface UseStorySessionTranscriptResult {
  hasTranscript: boolean;
  transcriptEntries: StoryTranscriptEntry[];
  isTranscriptDialogOpen: boolean;
  openTranscriptDialog: () => void;
  closeTranscriptDialog: () => void;
}

export function useStorySessionTranscript({
  messages,
}: UseStorySessionTranscriptOptions): UseStorySessionTranscriptResult {
  const [isTranscriptDialogRequested, setTranscriptDialogRequested] = useState(false);

  const transcriptEntries = useMemo(
    () =>
      messages
        .filter((message) => typeof message.content === 'string' && message.content.trim() !== '')
        .map((message, index) => ({
          id: `${message.role}-${index}`,
          role: message.role,
          roleLabel: ROLE_LABELS[message.role],
          content: message.content.trim(),
          sequenceNo: index + 1,
        })),
    [messages]
  );

  const isTranscriptDialogOpen = isTranscriptDialogRequested && transcriptEntries.length > 0;

  const openTranscriptDialog = useCallback(() => {
    if (transcriptEntries.length === 0) {
      return;
    }

    setTranscriptDialogRequested(true);
  }, [transcriptEntries.length]);

  const closeTranscriptDialog = useCallback(() => {
    setTranscriptDialogRequested(false);
  }, []);

  return {
    hasTranscript: transcriptEntries.length > 0,
    transcriptEntries,
    isTranscriptDialogOpen,
    openTranscriptDialog,
    closeTranscriptDialog,
  };
}
