import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import { checkServerHealth } from '@/services/healthApi';

export interface UseFirstStepFlowResult {
  loading: boolean;
  loadingMessage: string;
  continueGame: () => Promise<void>;
  startNewStory: () => void;
  exitToHome: () => void;
}

const delay = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

export function useFirstStepFlow(): UseFirstStepFlowResult {
  const navigate = useNavigate();
  const feedback = useFeedback();
  const { setRestoreSession, getResumeSave } = useGameFlow();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务器...');

  const continueGame = async () => {
    const saveData = getResumeSave();
    if (!saveData?.threadId) {
      feedback.warning('没有找到存档，请先开始新的故事。');
      return;
    }

    setLoading(true);
    setLoadingMessage('正在连接服务器...');

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        feedback.error('无法连接到服务器，请检查后端服务是否正在运行。');
        return;
      }

      setRestoreSession(saveData.threadId, saveData.characterId ?? null);
      setLoadingMessage('正在加载存档...');
      await delay(500);
      navigate(ROUTES.GAME);
    } catch {
      feedback.error('连接服务器失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  };

  const startNewStory = () => {
    navigate(ROUTES.CHARACTER_SETTING);
  };

  const exitToHome = () => {
    navigate(ROUTES.HOME);
  };

  return {
    loading,
    loadingMessage,
    continueGame,
    startNewStory,
    exitToHome,
  };
}
