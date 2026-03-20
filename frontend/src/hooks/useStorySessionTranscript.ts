import { useCallback, useEffect, useMemo, useState } from 'react';
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
  const [isTranscriptDialogOpen, setTranscriptDialogOpen] = useState(false);

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

  useEffect(() => {
    if (transcriptEntries.length === 0) {
      setTranscriptDialogOpen(false);
    }
  }, [transcriptEntries.length]);

  const openTranscriptDialog = useCallback(() => {
    if (transcriptEntries.length === 0) {
      return;
    }

    setTranscriptDialogOpen(true);
  }, [transcriptEntries.length]);

  const closeTranscriptDialog = useCallback(() => {
    setTranscriptDialogOpen(false);
  }, []);

  return {
    hasTranscript: transcriptEntries.length > 0,
    transcriptEntries,
    isTranscriptDialogOpen,
    openTranscriptDialog,
    closeTranscriptDialog,
  };
}
