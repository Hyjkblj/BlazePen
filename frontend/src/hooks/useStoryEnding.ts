import { useCallback, useEffect, useRef, useState } from 'react';
import { checkEnding } from '@/services/gameApi';
import { getServiceErrorMessage } from '@/services/serviceError';
import type { StoryEndingSummary } from '@/types/game';
import { logger } from '@/utils/logger';

export type StoryEndingStatus = 'idle' | 'loading' | 'ready' | 'unavailable' | 'error';

export interface UseStoryEndingOptions {
  threadId: string | null;
  isGameFinished: boolean;
}

export interface UseStoryEndingResult {
  isEndingDialogOpen: boolean;
  endingSummary: StoryEndingSummary | null;
  endingStatus: StoryEndingStatus;
  endingError: string | null;
  canViewEnding: boolean;
  openEndingDialog: () => void;
  closeEndingDialog: () => void;
  retryEndingSummary: () => void;
}

export function useStoryEnding({
  threadId,
  isGameFinished,
}: UseStoryEndingOptions): UseStoryEndingResult {
  const [isEndingDialogOpen, setEndingDialogOpen] = useState(false);
  const [endingSummary, setEndingSummary] = useState<StoryEndingSummary | null>(null);
  const [endingStatus, setEndingStatus] = useState<StoryEndingStatus>('idle');
  const [endingError, setEndingError] = useState<string | null>(null);
  const loadedThreadIdRef = useRef<string | null>(null);
  const loadingThreadIdRef = useRef<string | null>(null);

  const loadEndingSummary = useCallback(
    async (force = false) => {
      if (!threadId || !isGameFinished) {
        return;
      }

      const requestThreadId = threadId;
      const alreadyLoaded = loadedThreadIdRef.current === threadId;
      const alreadyLoading = loadingThreadIdRef.current === threadId;
      if (!force && (alreadyLoaded || alreadyLoading)) {
        return;
      }

      loadingThreadIdRef.current = requestThreadId;
      setEndingStatus('loading');
      setEndingError(null);

      try {
        const endingResult = await checkEnding(requestThreadId);
        if (loadingThreadIdRef.current !== requestThreadId) {
          return;
        }

        loadedThreadIdRef.current = requestThreadId;

        if (endingResult.hasEnding && endingResult.ending) {
          setEndingSummary(endingResult.ending);
          setEndingStatus('ready');
          return;
        }

        setEndingSummary(null);
        setEndingStatus('unavailable');
      } catch (error: unknown) {
        if (loadingThreadIdRef.current !== requestThreadId) {
          return;
        }

        logger.warn(`[story] failed to load ending summary for ${requestThreadId}`, error);
        setEndingSummary(null);
        setEndingStatus('error');
        setEndingError(getServiceErrorMessage(error, 'Failed to load ending summary.'));
      } finally {
        if (loadingThreadIdRef.current === requestThreadId) {
          loadingThreadIdRef.current = null;
        }
      }
    },
    [isGameFinished, threadId]
  );

  useEffect(() => {
    if (!threadId) {
      loadedThreadIdRef.current = null;
      loadingThreadIdRef.current = null;
      setEndingDialogOpen(false);
      setEndingSummary(null);
      setEndingStatus('idle');
      setEndingError(null);
      return;
    }

    if (!isGameFinished) {
      loadedThreadIdRef.current = null;
      loadingThreadIdRef.current = null;
      setEndingDialogOpen(false);
      setEndingSummary(null);
      setEndingStatus('idle');
      setEndingError(null);
      return;
    }

    if (loadedThreadIdRef.current !== threadId) {
      setEndingSummary(null);
      setEndingStatus('idle');
      setEndingError(null);
    }

    setEndingDialogOpen(true);
    void loadEndingSummary();
  }, [isGameFinished, loadEndingSummary, threadId]);

  const openEndingDialog = useCallback(() => {
    setEndingDialogOpen(true);
    if (threadId && isGameFinished && (endingStatus === 'idle' || endingStatus === 'error')) {
      void loadEndingSummary(endingStatus === 'error');
    }
  }, [endingStatus, isGameFinished, loadEndingSummary, threadId]);

  const closeEndingDialog = useCallback(() => {
    setEndingDialogOpen(false);
  }, []);

  const retryEndingSummary = useCallback(() => {
    setEndingDialogOpen(true);
    void loadEndingSummary(true);
  }, [loadEndingSummary]);

  return {
    isEndingDialogOpen,
    endingSummary,
    endingStatus,
    endingError,
    canViewEnding: Boolean(threadId && isGameFinished),
    openEndingDialog,
    closeEndingDialog,
    retryEndingSummary,
  };
}
