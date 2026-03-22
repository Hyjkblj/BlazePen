import { getTrainingProgress } from '@/services/trainingApi';
import type { TrainingProgressResult } from '@/types/training';
import { useTrainingReadQuery } from './useTrainingReadQuery';

export function useTrainingProgress(explicitSessionId?: string | null) {
  const query = useTrainingReadQuery<TrainingProgressResult>({
    explicitSessionId,
    fetcher: getTrainingProgress,
    fallbackErrorMessage: '读取训练进度失败。',
  });

  const totalRounds = query.data?.totalRounds ?? 0;
  const progressPercent =
    query.data && totalRounds > 0
      ? (Math.min(query.data.roundNo, totalRounds) / totalRounds) * 100
      : 0;

  return {
    ...query,
    totalRounds,
    progressPercent,
  };
}
