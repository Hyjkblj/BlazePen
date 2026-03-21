import { getTrainingReport } from '@/services/trainingApi';
import type { TrainingReportResult } from '@/types/training';
import { useTrainingReadQuery } from './useTrainingReadQuery';

export function useTrainingReport(explicitSessionId?: string | null) {
  return useTrainingReadQuery<TrainingReportResult>({
    explicitSessionId,
    fetcher: getTrainingReport,
    fallbackErrorMessage: '读取训练报告失败。',
  });
}
