import { useCallback, useEffect, useState } from 'react';
import type { TrainingSessionViewState } from '@/hooks/useTrainingSessionViewModel';
import { getServiceErrorMessage } from '@/services/serviceError';
import { getTrainingReport } from '@/services/trainingApi';
import type { TrainingReportResult } from '@/types/training';

type CompletionReportStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface UseTrainingCompletionReportFlowResult {
  completionReportStatus: CompletionReportStatus;
  completionReport: TrainingReportResult | null;
  completionReportErrorMessage: string | null;
  resetCompletionReportFlow: () => void;
}

export function useTrainingCompletionReportFlow(
  sessionView: TrainingSessionViewState | null
): UseTrainingCompletionReportFlowResult {
  const [completionReportStatus, setCompletionReportStatus] =
    useState<CompletionReportStatus>('idle');
  const [completionReport, setCompletionReport] = useState<TrainingReportResult | null>(null);
  const [completionReportErrorMessage, setCompletionReportErrorMessage] = useState<string | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      const sessionId = sessionView?.sessionId ?? null;
      if (!sessionId || !sessionView?.isCompleted) {
        if (!cancelled) {
          setCompletionReportStatus('idle');
          setCompletionReport(null);
          setCompletionReportErrorMessage(null);
        }
        return;
      }

      if (!cancelled) {
        setCompletionReportStatus('loading');
        setCompletionReportErrorMessage(null);
      }

      try {
        const report = await getTrainingReport(sessionId);
        if (cancelled) {
          return;
        }
        setCompletionReport(report);
        setCompletionReportStatus('ready');
      } catch (error: unknown) {
        if (cancelled) {
          return;
        }
        setCompletionReportStatus('error');
        setCompletionReport(null);
        setCompletionReportErrorMessage(
          getServiceErrorMessage(error, 'Training report is aggregating. Please refresh later.')
        );
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [sessionView?.isCompleted, sessionView?.sessionId]);

  const resetCompletionReportFlow = useCallback(() => {
    setCompletionReportStatus('idle');
    setCompletionReport(null);
    setCompletionReportErrorMessage(null);
  }, []);

  return {
    completionReportStatus,
    completionReport,
    completionReportErrorMessage,
    resetCompletionReportFlow,
  };
}
