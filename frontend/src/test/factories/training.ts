import type { TrainingMediaTaskResult } from '@/types/training';

export const makeTrainingMediaTask = (
  overrides: Partial<TrainingMediaTaskResult> = {}
): TrainingMediaTaskResult => ({
  taskId: 'task-1',
  sessionId: 'training-session-1',
  roundNo: 1,
  taskType: 'image',
  status: 'pending',
  result: null,
  error: null,
  createdAt: '2026-03-29T00:00:00Z',
  updatedAt: '2026-03-29T00:00:00Z',
  startedAt: null,
  finishedAt: null,
  ...overrides,
});

