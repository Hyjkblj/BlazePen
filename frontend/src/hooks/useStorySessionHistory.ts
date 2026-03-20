import { useCallback, useEffect, useRef, useState } from 'react';
import { getStorySessionHistory } from '@/services/gameApi';
import { getServiceErrorMessage } from '@/services/serviceError';
import type { StorySessionHistoryResult } from '@/types/game';
import { logger } from '@/utils/logger';

export type StoryHistoryStatus = 'idle' | 'loading' | 'ready' | 'empty' | 'error';

export interface UseStorySessionHistoryOptions {
  threadId: string | null;
}

export interface UseStorySessionHistoryResult {
  isHistoryDialogOpen: boolean;
  historySession: StorySessionHistoryResult | null;
  historyStatus: StoryHistoryStatus;
  historyError: string | null;
  canViewHistory: boolean;
  openHistoryDialog: () => void;
  closeHistoryDialog: () => void;
  retryHistoryLoad: () => void;
}

export function useStorySessionHistory({
  threadId,
}: UseStorySessionHistoryOptions): UseStorySessionHistoryResult {
  const [isHistoryDialogOpen, setHistoryDialogOpen] = useState(false);
  const [historySession, setHistorySession] = useState<StorySessionHistoryResult | null>(null);
  const [historyStatus, setHistoryStatus] = useState<StoryHistoryStatus>('idle');
  const [historyError, setHistoryError] = useState<string | null>(null);
  const loadedThreadIdRef = useRef<string | null>(null);
  const loadingThreadIdRef = useRef<string | null>(null);

  const loadHistory = useCallback(
    async (force = false) => {
      if (!threadId) {
        return;
      }

      const requestThreadId = threadId;
      const alreadyLoaded = loadedThreadIdRef.current === requestThreadId;
      const alreadyLoading = loadingThreadIdRef.current === requestThreadId;
      if (!force && (alreadyLoaded || alreadyLoading)) {
        return;
      }

      loadingThreadIdRef.current = requestThreadId;
      setHistoryStatus('loading');
      setHistoryError(null);

      try {
        const sessionHistory = await getStorySessionHistory(requestThreadId);
        if (loadingThreadIdRef.current !== requestThreadId) {
          return;
        }

        loadedThreadIdRef.current = requestThreadId;
        setHistorySession(sessionHistory);
        setHistoryStatus(sessionHistory.history.length > 0 ? 'ready' : 'empty');
      } catch (error: unknown) {
        if (loadingThreadIdRef.current !== requestThreadId) {
          return;
        }

        logger.warn(`[story] failed to load story history for ${requestThreadId}`, error);
        setHistorySession(null);
        setHistoryStatus('error');
        setHistoryError(getServiceErrorMessage(error, 'Failed to load story history.'));
      } finally {
        if (loadingThreadIdRef.current === requestThreadId) {
          loadingThreadIdRef.current = null;
        }
      }
    },
    [threadId]
  );

  useEffect(() => {
    if (!threadId) {
      loadedThreadIdRef.current = null;
      loadingThreadIdRef.current = null;
      setHistoryDialogOpen(false);
      setHistorySession(null);
      setHistoryStatus('idle');
      setHistoryError(null);
      return;
    }

    if (loadedThreadIdRef.current !== threadId) {
      setHistoryDialogOpen(false);
      setHistorySession(null);
      setHistoryStatus('idle');
      setHistoryError(null);
    }
  }, [threadId]);

  const openHistoryDialog = useCallback(() => {
    if (!threadId) {
      return;
    }

    setHistoryDialogOpen(true);
    if (historyStatus === 'idle' || historyStatus === 'error') {
      void loadHistory(historyStatus === 'error');
    }
  }, [historyStatus, loadHistory, threadId]);

  const closeHistoryDialog = useCallback(() => {
    setHistoryDialogOpen(false);
  }, []);

  const retryHistoryLoad = useCallback(() => {
    setHistoryDialogOpen(true);
    void loadHistory(true);
  }, [loadHistory]);

  return {
    isHistoryDialogOpen,
    historySession,
    historyStatus,
    historyError,
    canViewHistory: Boolean(threadId),
    openHistoryDialog,
    closeHistoryDialog,
    retryHistoryLoad,
  };
}
