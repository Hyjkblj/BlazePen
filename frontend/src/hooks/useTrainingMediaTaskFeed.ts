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
const EMPTY_MEDIA_TASKS: TrainingMediaTaskResult[] = [];

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

interface TrainingMediaTaskFeedState {
  sessionId: string | null;
  status: TrainingMediaTaskFeedStatus;
  errorMessage: string | null;
  rawTasks: TrainingMediaTaskResult[] | null;
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

const mergeSeedTaskRows = (
  rawTasks: TrainingMediaTaskResult[] | null,
  seedTasks: TrainingMediaTaskResult[]
): TrainingMediaTaskResult[] => {
  if (!rawTasks || rawTasks.length === 0) {
    return seedTasks;
  }

  if (seedTasks.length === 0) {
    return rawTasks;
  }

  const mergedByTaskId = new Map(rawTasks.map((task) => [task.taskId, task]));
  for (const seedTask of seedTasks) {
    if (!mergedByTaskId.has(seedTask.taskId)) {
      mergedByTaskId.set(seedTask.taskId, seedTask);
    }
  }

  return sortTrainingMediaTasks(Array.from(mergedByTaskId.values()));
};

const createTrainingMediaTaskFeedState = (): TrainingMediaTaskFeedState => ({
  sessionId: null,
  status: 'idle',
  errorMessage: null,
  rawTasks: null,
});

export function useTrainingMediaTaskFeed({
  sessionId,
  roundNo = null,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  seedTasks,
}: UseTrainingMediaTaskFeedOptions): UseTrainingMediaTaskFeedResult {
  const [feedState, setFeedState] = useState<TrainingMediaTaskFeedState>(
    createTrainingMediaTaskFeedState
  );
  const normalizedSeedTasks = seedTasks ?? EMPTY_SEED_TASKS;
  const seedTaskRows = useMemo(() => {
    if (!sessionId || normalizedSeedTasks.length === 0) {
      return EMPTY_MEDIA_TASKS;
    }

    return buildSeedTaskRows(sessionId, normalizedSeedTasks);
  }, [normalizedSeedTasks, sessionId]);

  const runRefresh = useCallback(async (silent = false) => {
    if (!sessionId) {
      return;
    }

    if (!silent) {
      setFeedState((current) => ({
        sessionId,
        rawTasks: current.sessionId === sessionId ? current.rawTasks : null,
        status: 'loading',
        errorMessage: null,
      }));
    }

    try {
      const result = await listTrainingMediaTasks({
        sessionId,
        roundNo,
      });
      const filteredTasks =
        roundNo === null ? result.items : result.items.filter((task) => task.roundNo === roundNo);
      setFeedState({
        sessionId,
        rawTasks: sortTrainingMediaTasks(filteredTasks),
        status: 'ready',
        errorMessage: null,
      });
    } catch (error: unknown) {
      if (!silent) {
        setFeedState((current) => ({
          sessionId,
          rawTasks: current.sessionId === sessionId ? current.rawTasks : null,
          status: 'error',
          errorMessage: getServiceErrorMessage(error, 'Failed to load media task status.'),
        }));
      }
    }
  }, [roundNo, sessionId]);

  const refresh = useCallback(async () => {
    await runRefresh(false);
  }, [runRefresh]);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    void runRefresh(false);
  }, [runRefresh, sessionId]);

  const currentRawTasks =
    sessionId && feedState.sessionId === sessionId ? feedState.rawTasks : null;
  const rawTasks = useMemo(
    () => mergeSeedTaskRows(currentRawTasks, seedTaskRows),
    [currentRawTasks, seedTaskRows]
  );
  const status =
    !sessionId ? 'idle' : feedState.sessionId === sessionId ? feedState.status : 'loading';
  const errorMessage =
    sessionId && feedState.sessionId === sessionId ? feedState.errorMessage : null;

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
