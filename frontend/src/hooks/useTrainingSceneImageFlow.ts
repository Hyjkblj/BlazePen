import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { TrainingSessionViewState } from '@/hooks/useTrainingSessionViewModel';
import { getServiceErrorMessage } from '@/services/serviceError';
import { createTrainingMediaTask, getTrainingMediaTask } from '@/services/trainingApi';
import type { TrainingMediaTaskStatus, TrainingScenario } from '@/types/training';
import { normalizeTrainingMediaTaskView } from '@/utils/trainingSession';

type SceneImageStatus = TrainingMediaTaskStatus | 'idle';
type SceneImageAttemptState = {
  lifecycleKey: string | null;
  value: number;
};

const ACTIVE_SCENE_IMAGE_STATUSES = new Set<TrainingMediaTaskStatus>(['pending', 'running']);
const SCENE_IMAGE_POLL_INTERVAL_MS = 3000;

const buildSceneImageIdempotencyKey = (sessionId: string, scenarioId: string): string =>
  `training-scene-image:${sessionId}:${scenarioId}`;

const buildSceneImageAttemptIdempotencyKey = (
  sessionId: string,
  scenarioId: string,
  attemptNo: number
): string => `${buildSceneImageIdempotencyKey(sessionId, scenarioId)}:attempt:${Math.max(0, attemptNo)}`;

const buildSceneImagePrompt = (scenario: TrainingScenario): string =>
  [
    `Scene title: ${scenario.title || 'Untitled scene'}`,
    `Era: ${scenario.eraDate || 'Unknown era'}`,
    `Location: ${scenario.location || 'Unknown location'}`,
    `Brief: ${scenario.brief || 'N/A'}`,
    `Mission: ${scenario.mission || 'N/A'}`,
    `Decision focus: ${scenario.decisionFocus || 'N/A'}`,
  ].join('\n');

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
      prompt: buildSceneImagePrompt(currentScenario),
      brief: currentScenario.brief,
      mission: currentScenario.mission,
      decisionFocus: currentScenario.decisionFocus,
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
  }, [sceneLifecycleKey]);

  useEffect(() => {
    let cancelled = false;

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

      const sceneImageRequestKey = `${sceneLifecycleKey}:attempt:${sceneImageAttemptNo}`;
      if (lastSceneImageRequestKeyRef.current === sceneImageRequestKey) {
        return;
      }
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
        const createdTask = await createTrainingMediaTask({
          sessionId: sceneImageContext.sessionId,
          roundNo: sceneImageContext.roundNo,
          taskType: 'image',
          idempotencyKey,
          maxRetries: 1,
          payload: {
            session_id: sceneImageContext.sessionId,
            round_no: sceneImageContext.roundNo,
            scenario_id: sceneImageContext.scenarioId,
            scenario_title: sceneImageContext.scenarioTitle,
            major_scene_title: sceneImageContext.scenarioTitle,
            prompt: sceneImageContext.prompt,
            scenario_prompt: sceneImageContext.prompt,
            brief: sceneImageContext.brief,
            mission: sceneImageContext.mission,
            decision_focus: sceneImageContext.decisionFocus,
            image_type: 'scene',
            generate_storyline_series: true,
            character_id: sceneImageContext.characterId,
          },
        });

        if (cancelled) {
          return;
        }

        const normalizedView = normalizeTrainingMediaTaskView(createdTask);
        setSceneImageTaskId(createdTask.taskId);
        setSceneImageStatus(createdTask.status);
        setSceneImageUrl(normalizedView.previewUrl);
        setSceneImageErrorMessage(normalizedView.errorMessage);
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
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
        const task = await getTrainingMediaTask(sceneImageTaskId);
        if (cancelled) {
          return;
        }

        const normalizedView = normalizeTrainingMediaTaskView(task);
        setSceneImageStatus(task.status);
        setSceneImageUrl(normalizedView.previewUrl);
        setSceneImageErrorMessage(normalizedView.errorMessage);
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
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
  }, [sceneImageStatus, sceneImageTaskId]);

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
