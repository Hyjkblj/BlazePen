import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import { readStoryResumeTarget } from '@/storage/storySessionCache';

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
  const { setRestoreSession } = useGameFlow();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务中...');

  const continueGame = async () => {
    const resumeTarget = readStoryResumeTarget();
    if (!resumeTarget?.threadId) {
      feedback.warning('没有找到可继续的故事记录，请先开始新的故事。');
      return;
    }

    setLoading(true);
    setLoadingMessage(
      resumeTarget.source === 'active-session' ? '正在恢复当前故事会话...' : '正在加载故事记录...'
    );

    try {
      setRestoreSession(resumeTarget.threadId, resumeTarget.characterId ?? null);
      await delay(500);
      navigate(ROUTES.GAME);
    } catch {
      feedback.error('继续故事失败，请稍后重试。');
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
