import { useEffect, useRef, useState } from 'react';
import httpClient, { unwrapApiData } from '@/services/httpClient';

export type StoryScriptLoadStatus = 'idle' | 'loading' | 'ready' | 'unavailable';

export interface UseStoryScriptPayloadResult {
  payload: unknown;
  status: StoryScriptLoadStatus;
}

interface CacheEntry {
  payload: unknown;
  status: StoryScriptLoadStatus;
}

const RETRY_DELAY_MS = 3000;
const MAX_RETRIES = 2;
const POLL_STATUS = new Set(['pending', 'running']);

/**
 * Fetches and caches the StoryScriptPayload for a given sessionId.
 * - Same sessionId is only fetched once (cached in useRef).
 * - When the API response status is `pending` or `running`, retries after 3s, up to 2 times.
 * - On failure, status is set to `unavailable` and payload is null.
 * - Does not block the main flow (async fetch).
 *
 * Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
 */
export function useStoryScriptPayload(
  sessionId: string | null | undefined
): UseStoryScriptPayloadResult {
  const cacheRef = useRef<Map<string, CacheEntry>>(new Map());
  const [result, setResult] = useState<UseStoryScriptPayloadResult>({
    payload: null,
    status: 'idle',
  });

  useEffect(() => {
    if (!sessionId) {
      setResult({ payload: null, status: 'idle' });
      return;
    }

    const cached = cacheRef.current.get(sessionId);
    if (cached) {
      setResult({ payload: cached.payload, status: cached.status });
      return;
    }

    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const fetchPayload = async (retriesLeft: number): Promise<void> => {
      if (cancelled) return;

      setResult({ payload: null, status: 'loading' });

      try {
        const response = await httpClient.get(`/v1/training/story-scripts/${sessionId}`);
        if (cancelled) return;

        const data = unwrapApiData<Record<string, unknown>>(response);
        const scriptStatus =
          typeof data?.status === 'string' ? data.status : null;

        if (scriptStatus && POLL_STATUS.has(scriptStatus)) {
          // `pending/running` are non-terminal statuses. Keep polling and never
          // cache them as `ready`, otherwise the same session would be stuck.
          const nextRetriesLeft = retriesLeft > 0 ? retriesLeft - 1 : MAX_RETRIES;
          retryTimer = setTimeout(() => {
            void fetchPayload(nextRetriesLeft);
          }, RETRY_DELAY_MS);
          return;
        }

        if (scriptStatus === 'failed' || scriptStatus === 'error') {
          const entry: CacheEntry = { payload: null, status: 'unavailable' };
          cacheRef.current.set(sessionId, entry);
          setResult({ payload: null, status: 'unavailable' });
          return;
        }

        const entry: CacheEntry = { payload: data, status: 'ready' };
        cacheRef.current.set(sessionId, entry);
        setResult({ payload: data, status: 'ready' });
      } catch {
        if (cancelled) return;
        const entry: CacheEntry = { payload: null, status: 'unavailable' };
        cacheRef.current.set(sessionId, entry);
        setResult({ payload: null, status: 'unavailable' });
      }
    };

    void fetchPayload(MAX_RETRIES);

    return () => {
      cancelled = true;
      if (retryTimer !== null) {
        clearTimeout(retryTimer);
      }
    };
  }, [sessionId]);

  return result;
}
