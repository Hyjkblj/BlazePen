import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { checkServerHealth } from '@/services/healthApi';
import { readTrainingResumeTarget } from '@/storage/trainingSessionCache';

export interface UseHomeFlowResult {
  loading: boolean;
  errorMessage: string | null;
  hasTrainingResumeTarget: boolean;
  beginStory: () => Promise<void>;
  openTraining: () => void;
}

export function useHomeFlow(): UseHomeFlowResult {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const trainingResumeTarget = readTrainingResumeTarget();

  const beginStory = async () => {
    setErrorMessage(null);
    setLoading(true);

    try {
      const isHealthy = await checkServerHealth();
      if (isHealthy) {
        navigate(ROUTES.FIRST_STEP);
        return;
      }

      setErrorMessage('无法连接到服务器，请检查后端服务是否正在运行。');
    } catch {
      setErrorMessage('连接服务器失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  };

  const openTraining = () => {
    navigate(ROUTES.TRAINING);
  };

  return {
    loading,
    errorMessage,
    hasTrainingResumeTarget: Boolean(
      trainingResumeTarget?.sessionId && trainingResumeTarget.status !== 'completed'
    ),
    beginStory,
    openTraining,
  };
}
