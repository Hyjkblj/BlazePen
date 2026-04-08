// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import {
  buildTrainingSceneImageMediaTaskCreateParams,
  createTrainingMediaTask,
  getTrainingMediaTask,
} from '@/services/trainingApi';
import { useTrainingSceneImageFlow } from './useTrainingSceneImageFlow';

vi.mock('@/services/trainingApi', () => ({
  createTrainingMediaTask: vi.fn(),
  getTrainingMediaTask: vi.fn(),
  buildTrainingSceneImageMediaTaskCreateParams: vi.fn((params: any) => ({
    sessionId: params.sessionId,
    roundNo: params.roundNo,
    taskType: 'image',
    idempotencyKey: `training-scene-image:${params.sessionId}:${params.scenario?.id}:attempt:${Math.max(
      0,
      Math.floor(params.attemptNo ?? 0)
    )}`,
    maxRetries: 1,
    payload: {},
  })),
}));

const createScenario = (id: string, title: string) => ({
  id,
  title,
  eraDate: '1941-06-14',
  location: 'Shanghai',
  brief: `${title} brief`,
  mission: 'Protect the source while filing the story.',
  decisionFocus: 'Choose the safest next move.',
  targetSkills: ['verification'],
  riskTags: ['exposure'],
  options: [
    { id: `${id}-opt-1`, label: 'Hold publication', impactHint: 'Protect source safety' },
    { id: `${id}-opt-2`, label: 'Clarify source chain', impactHint: 'Expand evidence scope' },
    { id: `${id}-opt-3`, label: 'Escalate to editor desk', impactHint: 'Reduce field risk first' },
  ],
  completionHint: '',
  recommendation: null,
});

const createSessionView = (sessionId: string, scenarioId: string) => ({
  sessionId,
  characterId: '42',
  trainingMode: 'guided',
  status: 'in_progress',
  roundNo: 0,
  totalRounds: 6,
  currentScenario: createScenario(scenarioId, 'Adopt existing task'),
  scenarioCandidates: [],
  resumableScenario: null,
  canResume: false,
  isCompleted: false,
  createdAt: null,
  updatedAt: null,
  endTime: null,
} as any);

describe('useTrainingSceneImageFlow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  it('adopts existing task id on 409 conflict and polls it without retrying create', async () => {
    vi.mocked(createTrainingMediaTask).mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_MEDIA_TASK_CONFLICT',
        status: 409,
        message: 'conflict',
        details: {
          existingTaskId: 'task-existing-1',
          scope: {
            sessionId: 'session-1',
            roundNo: 1,
          },
          idempotencyKey: 'training-scene-image:session-1:scenario-1:attempt:0',
        },
      })
    );
    vi.mocked(getTrainingMediaTask).mockResolvedValueOnce({
      taskId: 'task-existing-1',
      sessionId: 'session-1',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      idempotencyKey: 'training-scene-image:session-1:scenario-1:attempt:0',
      request: {},
      result: { preview_url: '/static/images/training/scenes/existing.png' },
      error: null,
      createdAt: '2026-03-25T12:00:00Z',
      updatedAt: '2026-03-25T12:00:01Z',
      startedAt: null,
      finishedAt: null,
    } as any);

    const sessionView = createSessionView('session-1', 'scenario-1');
    const { result } = renderHook(() => useTrainingSceneImageFlow(sessionView));

    expect(createTrainingMediaTask).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3100);
      await Promise.resolve();
    });

    expect(result.current.sceneImageStatus).toBe('succeeded');
    expect(getTrainingMediaTask).toHaveBeenCalledTimes(1);
    expect(getTrainingMediaTask).toHaveBeenCalledWith('task-existing-1');
    expect(result.current.sceneImageUrl).toBe('/static/images/training/scenes/existing.png');

    // Ensure we did not spin a second create attempt after adopting.
    expect(createTrainingMediaTask).toHaveBeenCalledTimes(1);
  });

  it('passes narrative visual_prompt into scene image task params when available', async () => {
    vi.mocked(createTrainingMediaTask).mockResolvedValueOnce({
      taskId: 'task-visual-1',
      sessionId: 'session-2',
      roundNo: 1,
      taskType: 'image',
      status: 'succeeded',
      idempotencyKey: 'training-scene-image:session-2:scenario-2:attempt:0',
      request: {},
      result: { preview_url: '/static/images/training/scenes/visual.png' },
      error: null,
      createdAt: '2026-03-25T12:00:00Z',
      updatedAt: '2026-03-25T12:00:01Z',
      startedAt: null,
      finishedAt: null,
    } as any);

    const sessionView = createSessionView('session-2', 'scenario-2');
    const storyScriptPayload = {
      version: 'training_story_script_v2',
      narratives: {
        'scenario-2': {
          monologue: '独白',
          dialogue: [],
          bridge_summary: '',
          options_narrative: {},
          visual_prompt: '战地街道，烟雾弥漫，远处火光，记者隐蔽观察',
          visual_elements: ['战地街道', '烟雾', '远处火光'],
        },
      },
    };

    renderHook(() => useTrainingSceneImageFlow(sessionView, storyScriptPayload));

    await act(async () => {
      await Promise.resolve();
    });

    expect(buildTrainingSceneImageMediaTaskCreateParams).toHaveBeenCalledWith(
      expect.objectContaining({
        sessionId: 'session-2',
        visualPrompt: '战地街道，烟雾弥漫，远处火光，记者隐蔽观察',
      })
    );
  });
});
