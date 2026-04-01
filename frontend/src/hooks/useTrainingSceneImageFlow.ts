import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TrainingSessionViewState } from '@/hooks/useTrainingSessionViewModel';
import { getServiceErrorMessage, ServiceError } from '@/services/serviceError';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import {
  buildTrainingSceneImageMediaTaskCreateParams,
  createTrainingMediaTask,
  getTrainingMediaTask,
} from '@/services/trainingApi';
import type { TrainingMediaTaskStatus, TrainingScenario } from '@/types/training';
import { normalizeTrainingMediaTaskView } from '@/utils/trainingSession';

type SceneImageStatus = TrainingMediaTaskStatus | 'idle';
type SceneImageAttemptState = {
  lifecycleKey: string | null;
  value: number;
};

// Treat `unknown` as active so new backend statuses still get polled.
const ACTIVE_SCENE_IMAGE_STATUSES = new Set<TrainingMediaTaskStatus>(['pending', 'running', 'unknown']);
const FINAL_SCENE_IMAGE_STATUSES = new Set<TrainingMediaTaskStatus>(['succeeded', 'failed', 'timeout']);
const SCENE_IMAGE_POLL_INTERVAL_MS = 3000;

const buildSceneImageIdempotencyKey = (sessionId: string, scenarioId: string): string =>
  `training-scene-image:${sessionId}:${scenarioId}`;

const buildSceneImageAttemptIdempotencyKey = (
  sessionId: string,
  scenarioId: string,
  attemptNo: number
): string => `${buildSceneImageIdempotencyKey(sessionId, scenarioId)}:attempt:${Math.max(0, attemptNo)}`;

const normalizeUrlKind = (value: string | null | undefined): 'empty' | 'absolute' | 'relative' | 'other' => {
  const url = String(value ?? '').trim();
  if (!url) return 'empty';
  if (/^(https?:|data:|blob:|file:)/i.test(url)) return 'absolute';
  if (url.startsWith('/')) return 'relative';
  return 'other';
};

const readConflictScope = (
  error: unknown
): { taskId: string; sessionId: string | null; roundNo: number | null; idempotencyKey: string | null } | null => {
  if (!(error instanceof ServiceError)) {
    return null;
  }
  if (error.code !== 'TRAINING_MEDIA_TASK_CONFLICT' || error.status !== 409) {
    return null;
  }
  if (!error.details || typeof error.details !== 'object') {
    return null;
  }
  const details = error.details as Record<string, unknown>;
  const existingTaskId = details.existingTaskId;
  const scope = details.scope as Record<string, unknown> | null;
  if (typeof existingTaskId !== 'string' || existingTaskId.trim() === '') {
    return null;
  }
  const sessionId =
    typeof scope?.sessionId === 'string' && scope.sessionId.trim() ? scope.sessionId.trim() : null;
  const roundNo =
    typeof scope?.roundNo === 'number' && Number.isFinite(scope.roundNo) ? scope.roundNo : null;
  const idempotencyKey =
    typeof details.idempotencyKey === 'string' && details.idempotencyKey.trim()
      ? details.idempotencyKey.trim()
      : null;
  return { taskId: existingTaskId.trim(), sessionId, roundNo, idempotencyKey };
};

export interface UseTrainingSceneImageFlowResult {
  sceneImageStatus: SceneImageStatus;
  sceneImageUrl: string | null;
  sceneImageErrorMessage: string | null;
  retrySceneImage: () => void;
  resetSceneImageFlow: () => void;
}

export function useTrainingSceneImageFlow(
  sessionView: TrainingSessionViewState | null
): UseTrainingSceneImageFlowResult {
  const [sceneImageTaskId, setSceneImageTaskId] = useState<string | null>(null);
  const [sceneImageStatus, setSceneImageStatus] = useState<SceneImageStatus>('idle');
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [sceneImageErrorMessage, setSceneImageErrorMessage] = useState<string | null>(null);
  const [sceneImageAttemptState, setSceneImageAttemptState] = useState<SceneImageAttemptState>({
    lifecycleKey: null,
    value: 0,
  });
  const lastSceneLifecycleKeyRef = useRef<string | null>(null);
  const lastSceneImageRequestKeyRef = useRef<string | null>(null);
  const sceneImageTaskLifecycleKeyRef = useRef<string | null>(null);

  const sceneImageContext = useMemo(() => {
    const sessionId = sessionView?.sessionId ?? null;
    const currentScenario = sessionView?.currentScenario ?? null;
    if (!sessionId || !currentScenario) {
      return null;
    }
    return {
      sessionId,
      scenarioId: currentScenario.id,
      scenarioTitle: currentScenario.title,
      roundNo: Math.max((sessionView?.roundNo ?? 0) + 1, 1),
      scenario: currentScenario,
      characterId: sessionView?.characterId ?? null,
      isCompleted: Boolean(sessionView?.isCompleted),
    };
  }, [
    sessionView?.characterId,
    sessionView?.currentScenario,
    sessionView?.isCompleted,
    sessionView?.roundNo,
    sessionView?.sessionId,
  ]);

  const sceneLifecycleKey = useMemo(() => {
    if (!sceneImageContext) {
      return null;
    }
    return `${sceneImageContext.sessionId}:${sceneImageContext.scenarioId}`;
  }, [sceneImageContext]);

  const sceneImageAttemptNo = useMemo(() => {
    if (!sceneLifecycleKey) {
      return 0;
    }
    if (sceneImageAttemptState.lifecycleKey !== sceneLifecycleKey) {
      return 0;
    }
    return sceneImageAttemptState.value;
  }, [sceneImageAttemptState, sceneLifecycleKey]);

  useEffect(() => {
    if (sceneLifecycleKey === lastSceneLifecycleKeyRef.current) {
      return;
    }
    lastSceneLifecycleKeyRef.current = sceneLifecycleKey;
    lastSceneImageRequestKeyRef.current = null;
    sceneImageTaskLifecycleKeyRef.current = null;
    setSceneImageTaskId(null);
    setSceneImageStatus('idle');
    setSceneImageUrl(null);
    setSceneImageErrorMessage(null);
  }, [sceneLifecycleKey]);

  useEffect(() => {
    let cancelled = false;
    let requestKeyForCleanup: string | null = null;

    const run = async () => {
      if (!sceneImageContext || !sceneLifecycleKey || sceneImageContext.isCompleted) {
        if (!cancelled) {
          setSceneImageTaskId(null);
          setSceneImageStatus('idle');
          setSceneImageUrl(null);
          setSceneImageErrorMessage(null);
        }
        return;
      }

      // If we already have a task for this lifecycle, avoid creating a new one.
      // Polling (if needed) is handled by the polling effect keyed by sceneImageTaskId/status.
      if (sceneImageTaskId && sceneImageTaskLifecycleKeyRef.current === sceneLifecycleKey) {
        return;
      }

      const sceneImageRequestKey = `${sceneLifecycleKey}:attempt:${sceneImageAttemptNo}`;
      requestKeyForCleanup = sceneImageRequestKey;
      if (lastSceneImageRequestKeyRef.current === sceneImageRequestKey) {
        return;
      }
      // Mark the request key as in-flight. If this effect gets cancelled before the request
      // resolves, we'll clear the key in cleanup so the next render can retry.
      lastSceneImageRequestKeyRef.current = sceneImageRequestKey;

      if (!cancelled) {
        setSceneImageTaskId(null);
        setSceneImageStatus('pending');
        setSceneImageUrl(null);
        setSceneImageErrorMessage(null);
      }

      const idempotencyKey = buildSceneImageAttemptIdempotencyKey(
        sceneImageContext.sessionId,
        sceneImageContext.scenarioId,
        sceneImageAttemptNo
      );

      try {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.scene_image.create' as any,
          status: 'requested',
          metadata: {
            sessionId: sceneImageContext.sessionId,
            scenarioId: sceneImageContext.scenarioId,
            attemptNo: sceneImageAttemptNo,
            sceneLifecycleKey,
            idempotencyKey,
          },
        });
        const createdTask = await createTrainingMediaTask(
          buildTrainingSceneImageMediaTaskCreateParams({
            sessionId: sceneImageContext.sessionId,
            roundNo: sceneImageContext.roundNo,
            scenario: sceneImageContext.scenario,
            attemptNo: sceneImageAttemptNo,
            // Default: do not force storyline-series generation from the hook.
            generateStorylineSeries: false,
          })
        );

        if (cancelled) {
          return;
        }

        const normalizedView = normalizeTrainingMediaTaskView(createdTask);
        sceneImageTaskLifecycleKeyRef.current = sceneLifecycleKey;
        setSceneImageTaskId(createdTask.taskId);
        const shouldPoll =
          createdTask.taskType === 'image' &&
          !normalizedView.previewUrl &&
          !FINAL_SCENE_IMAGE_STATUSES.has(createdTask.status);
        setSceneImageStatus(shouldPoll ? 'running' : createdTask.status);
        setSceneImageUrl(normalizedView.previewUrl);
        setSceneImageErrorMessage(normalizedView.errorMessage);

        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.scene_image.create' as any,
          status: 'succeeded',
          metadata: {
            sessionId: sceneImageContext.sessionId,
            scenarioId: sceneImageContext.scenarioId,
            attemptNo: sceneImageAttemptNo,
            taskId: createdTask.taskId,
            taskStatus: createdTask.status,
            shouldPoll,
            hasPreviewUrl: Boolean(normalizedView.previewUrl),
            previewUrlKind: normalizeUrlKind(normalizedView.previewUrl),
            staticAssetOrigin: (import.meta.env.VITE_STATIC_ASSET_ORIGIN ?? '').trim() || null,
          },
        });
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
        const conflictScope = readConflictScope(error);
        if (conflictScope) {
          const shouldAdoptExistingTask =
            (!conflictScope.sessionId || conflictScope.sessionId === sceneImageContext.sessionId) &&
            (conflictScope.roundNo === null || conflictScope.roundNo === sceneImageContext.roundNo);
          trackFrontendTelemetry({
            domain: 'training',
            event: 'training.scene_image.create' as any,
            status: 'failed',
            metadata: {
              sessionId: sceneImageContext.sessionId,
              scenarioId: sceneImageContext.scenarioId,
              attemptNo: sceneImageAttemptNo,
              sceneLifecycleKey,
              idempotencyKey,
              recoveredExistingTaskId: conflictScope.taskId,
              recoveredTaskSessionId: conflictScope.sessionId,
              recoveredTaskRoundNo: conflictScope.roundNo,
              recoveredTaskIdempotencyKey: conflictScope.idempotencyKey,
              recoveryAction: shouldAdoptExistingTask ? 'adopt_existing_task' : 'retry_new_attempt',
            },
            cause: error,
          });
          if (shouldAdoptExistingTask) {
            sceneImageTaskLifecycleKeyRef.current = sceneLifecycleKey;
            setSceneImageTaskId(conflictScope.taskId);
            setSceneImageStatus('running');
            setSceneImageUrl(null);
            setSceneImageErrorMessage(null);
            return;
          }
          // Conflict scope mismatched: do not risk showing wrong image; retry with a new attempt key.
          lastSceneImageRequestKeyRef.current = null;
          setSceneImageAttemptState((current) => ({
            lifecycleKey: sceneLifecycleKey,
            value: current.lifecycleKey === sceneLifecycleKey ? current.value + 1 : 1,
          }));
          return;
        }
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.scene_image.create' as any,
          status: 'failed',
          metadata: {
            sessionId: sceneImageContext.sessionId,
            scenarioId: sceneImageContext.scenarioId,
            attemptNo: sceneImageAttemptNo,
            sceneLifecycleKey,
            idempotencyKey,
          },
          cause: error,
        });
        setSceneImageStatus('failed');
        setSceneImageTaskId(null);
        setSceneImageErrorMessage(
          getServiceErrorMessage(error, 'Scene image generation failed. You can continue this round.')
        );
      }
    };

    void run();

    return () => {
      cancelled = true;
      // If we were cancelled mid-flight, allow the next effect run to retry the same key.
      if (requestKeyForCleanup && lastSceneImageRequestKeyRef.current === requestKeyForCleanup) {
        lastSceneImageRequestKeyRef.current = null;
      }
    };
  }, [sceneImageAttemptNo, sceneImageContext, sceneLifecycleKey]);

  useEffect(() => {
    if (
      !sceneImageTaskId ||
      sceneImageStatus === 'idle' ||
      !ACTIVE_SCENE_IMAGE_STATUSES.has(sceneImageStatus)
    ) {
      return;
    }

    let cancelled = false;

    const syncTask = async () => {
      try {
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.scene_image.poll' as any,
          status: 'requested',
          metadata: {
            taskId: sceneImageTaskId,
            lastKnownStatus: sceneImageStatus,
            sessionId: sceneImageContext?.sessionId ?? null,
            scenarioId: sceneImageContext?.scenarioId ?? null,
            sceneLifecycleKey,
          },
        });
        const task = await getTrainingMediaTask(sceneImageTaskId);
        if (cancelled) {
          return;
        }

        const normalizedView = normalizeTrainingMediaTaskView(task);
        setSceneImageStatus(task.status);
        setSceneImageUrl(normalizedView.previewUrl);
        setSceneImageErrorMessage(normalizedView.errorMessage);

        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.scene_image.poll' as any,
          status: 'succeeded',
          metadata: {
            taskId: sceneImageTaskId,
            taskStatus: task.status,
            hasPreviewUrl: Boolean(normalizedView.previewUrl),
            previewUrlKind: normalizeUrlKind(normalizedView.previewUrl),
            staticAssetOrigin: (import.meta.env.VITE_STATIC_ASSET_ORIGIN ?? '').trim() || null,
            sessionId: sceneImageContext?.sessionId ?? null,
            scenarioId: sceneImageContext?.scenarioId ?? null,
            sceneLifecycleKey,
          },
        });
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.scene_image.poll' as any,
          status: 'failed',
          metadata: {
            taskId: sceneImageTaskId,
            lastKnownStatus: sceneImageStatus,
            sessionId: sceneImageContext?.sessionId ?? null,
            scenarioId: sceneImageContext?.scenarioId ?? null,
            sceneLifecycleKey,
          },
          cause: error,
        });
        setSceneImageStatus('failed');
        setSceneImageErrorMessage(
          getServiceErrorMessage(
            error,
            'Failed to sync scene image status. You can continue this round first.'
          )
        );
      }
    };

    void syncTask();
    const timerId = window.setInterval(() => {
      void syncTask();
    }, SCENE_IMAGE_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [sceneImageStatus, sceneImageTaskId, sceneImageContext, sceneLifecycleKey]);

  const retrySceneImage = useCallback(() => {
    if (!sessionView?.sessionId || !sessionView.currentScenario || sessionView.isCompleted || !sceneLifecycleKey) {
      return;
    }
    setSceneImageTaskId(null);
    setSceneImageStatus('pending');
    setSceneImageUrl(null);
    setSceneImageErrorMessage(null);
    setSceneImageAttemptState((current) => ({
      lifecycleKey: sceneLifecycleKey,
      value: current.lifecycleKey === sceneLifecycleKey ? current.value + 1 : 1,
    }));
  }, [sceneLifecycleKey, sessionView]);

  const resetSceneImageFlow = useCallback(() => {
    setSceneImageTaskId(null);
    setSceneImageStatus('idle');
    setSceneImageUrl(null);
    setSceneImageErrorMessage(null);
    setSceneImageAttemptState({
      lifecycleKey: null,
      value: 0,
    });
    lastSceneLifecycleKeyRef.current = null;
    lastSceneImageRequestKeyRef.current = null;
  }, []);

  return {
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    retrySceneImage,
    resetSceneImageFlow,
  };
}
