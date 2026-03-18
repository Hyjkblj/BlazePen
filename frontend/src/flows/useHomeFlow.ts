import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { checkServerHealth } from '@/services/healthApi';

export interface UseHomeFlowResult {
  loading: boolean;
  errorMessage: string | null;
  beginStory: () => Promise<void>;
}

export function useHomeFlow(): UseHomeFlowResult {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  return {
    loading,
    errorMessage,
    beginStory,
  };
}
