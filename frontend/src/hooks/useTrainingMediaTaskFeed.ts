import { useCallback, useEffect, useMemo, useState } from 'react';
import { getServiceErrorMessage } from '@/services/serviceError';
import { listTrainingMediaTasks } from '@/services/trainingApi';
import type {
  TrainingMediaTaskResult,
  TrainingMediaTaskView,
  TrainingRoundSubmitMediaTaskSummary,
} from '@/types/training';
import { normalizeTrainingMediaTaskView } from '@/utils/trainingSession';

const ACTIVE_MEDIA_TASK_STATUSES = new Set<TrainingMediaTaskResult['status']>(['pending', 'running']);
const DEFAULT_POLL_INTERVAL_MS = 3000;
const EMPTY_SEED_TASKS: TrainingRoundSubmitMediaTaskSummary[] = [];

export type TrainingMediaTaskFeedStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface UseTrainingMediaTaskFeedOptions {
  sessionId: string | null;
  roundNo?: number | null;
  pollIntervalMs?: number;
  seedTasks?: TrainingRoundSubmitMediaTaskSummary[];
}

export interface UseTrainingMediaTaskFeedResult {
  status: TrainingMediaTaskFeedStatus;
  errorMessage: string | null;
  tasks: TrainingMediaTaskView[];
  isPolling: boolean;
  refresh: () => Promise<void>;
}

const sortTrainingMediaTasks = (tasks: TrainingMediaTaskResult[]): TrainingMediaTaskResult[] =>
  [...tasks].sort((left, right) => {
    const leftUpdatedAt = left.updatedAt ?? left.createdAt ?? '';
    const rightUpdatedAt = right.updatedAt ?? right.createdAt ?? '';
    if (leftUpdatedAt && rightUpdatedAt) {
      return rightUpdatedAt.localeCompare(leftUpdatedAt);
    }
    return right.taskId.localeCompare(left.taskId);
  });

const buildSeedTaskRows = (
  sessionId: string,
  seedTasks: TrainingRoundSubmitMediaTaskSummary[]
): TrainingMediaTaskResult[] =>
  seedTasks.map((task) => ({
    taskId: task.taskId,
    sessionId,
    roundNo: null,
    taskType: task.taskType,
    status: ['pending', 'running', 'succeeded', 'failed', 'timeout'].includes(task.status)
      ? (task.status as TrainingMediaTaskResult['status'])
      : 'unknown',
    result: null,
    error: null,
    createdAt: null,
    updatedAt: null,
    startedAt: null,
    finishedAt: null,
  }));

export function useTrainingMediaTaskFeed({
  sessionId,
  roundNo = null,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  seedTasks,
}: UseTrainingMediaTaskFeedOptions): UseTrainingMediaTaskFeedResult {
  const [status, setStatus] = useState<TrainingMediaTaskFeedStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [rawTasks, setRawTasks] = useState<TrainingMediaTaskResult[]>([]);
  const normalizedSeedTasks = seedTasks ?? EMPTY_SEED_TASKS;

  const runRefresh = useCallback(async (silent = false) => {
    if (!sessionId) {
      setRawTasks([]);
      setStatus('idle');
      setErrorMessage(null);
      return;
    }

    if (!silent) {
      setStatus('loading');
      setErrorMessage(null);
    }

    try {
      const result = await listTrainingMediaTasks({
        sessionId,
        roundNo,
      });
      const filteredTasks =
        roundNo === null ? result.items : result.items.filter((task) => task.roundNo === roundNo);
      setRawTasks(sortTrainingMediaTasks(filteredTasks));
      setStatus('ready');
      if (silent) {
        setErrorMessage(null);
      }
    } catch (error: unknown) {
      if (!silent) {
        setStatus('error');
        setErrorMessage(getServiceErrorMessage(error, 'Failed to load media task status.'));
      }
    }
  }, [roundNo, sessionId]);

  const refresh = useCallback(async () => {
    await runRefresh(false);
  }, [runRefresh]);

  useEffect(() => {
    if (!sessionId) {
      setRawTasks([]);
      setStatus('idle');
      setErrorMessage(null);
      return;
    }

    if (normalizedSeedTasks.length > 0) {
      setRawTasks(buildSeedTaskRows(sessionId, normalizedSeedTasks));
    } else {
      setRawTasks([]);
    }

    void runRefresh(false);
  }, [normalizedSeedTasks, runRefresh, sessionId]);

  const hasInFlightTasks = useMemo(
    () => rawTasks.some((task) => ACTIVE_MEDIA_TASK_STATUSES.has(task.status)),
    [rawTasks]
  );
  const tasks = useMemo(() => rawTasks.map((task) => normalizeTrainingMediaTaskView(task)), [rawTasks]);

  useEffect(() => {
    if (!sessionId || !hasInFlightTasks) {
      return;
    }

    const timer = window.setInterval(() => {
      void runRefresh(true);
    }, Math.max(pollIntervalMs, 1000));

    return () => {
      window.clearInterval(timer);
    };
  }, [hasInFlightTasks, pollIntervalMs, runRefresh, sessionId]);

  return {
    status,
    errorMessage,
    tasks,
    isPolling: hasInFlightTasks && Boolean(sessionId),
    refresh,
  };
}
