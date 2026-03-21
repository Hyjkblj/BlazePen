import { getTrainingProgress } from '@/services/trainingApi';
import type { TrainingProgressResult } from '@/types/training';
import { useTrainingReadQuery } from './useTrainingReadQuery';

export function useTrainingProgress(explicitSessionId?: string | null) {
  return useTrainingReadQuery<TrainingProgressResult>({
    explicitSessionId,
    fetcher: getTrainingProgress,
    fallbackErrorMessage: '读取训练进度失败。',
  });
}
