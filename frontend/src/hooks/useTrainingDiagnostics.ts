import { getTrainingDiagnostics } from '@/services/trainingApi';
import type { TrainingDiagnosticsResult } from '@/types/training';
import { useTrainingReadQuery } from './useTrainingReadQuery';

export function useTrainingDiagnostics(explicitSessionId?: string | null) {
  return useTrainingReadQuery<TrainingDiagnosticsResult>({
    explicitSessionId,
    fetcher: getTrainingDiagnostics,
    fallbackErrorMessage: '加载学情诊断失败。',
  });
}
