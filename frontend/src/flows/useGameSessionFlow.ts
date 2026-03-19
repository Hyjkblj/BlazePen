import { useEffect, useRef } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import { useGameInit, useGameState, useGameTts } from '@/hooks';
import { initGame, processGameInput } from '@/services/gameApi';
import type { GameTurnResult, PlayerOption } from '@/types/game';
import { resolvePreferredCharacterId } from '@/utils/gameSession';
import { logger } from '@/utils/logger';
import { resolveSceneDisplayName, resolveStorySceneVisual } from '@/utils/storyScene';

export interface UseGameSessionFlowResult {
  actNumber: number;
  showTransition: boolean;
  transitionSceneName: string;
  loading: boolean;
  shouldUseComposite: boolean;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  currentDialogue: string;
  currentOptions: PlayerOption[];
  dismissTransition: () => void;
  handleCharacterAssetError: () => void;
  handleCompositeAssetError: () => void;
  handleSceneAssetError: () => void;
  selectOption: (optionIndex: number) => Promise<void>;
}

export function useGameSessionFlow(): UseGameSessionFlowResult {
  const feedback = useFeedback();
  const { state: flowState, setActiveSession } = useGameFlow();
  const gameState = useGameState();
  const { actions, derived } = gameState;
  const { saveGameProgress, setCharacterImage } = useGameInit(actions);

  const {
    actNumber,
    showTransition,
    transitionSceneName,
    loading,
    shouldUseComposite,
    compositeImageUrl,
    sceneImageUrl,
    characterImageUrl,
    currentDialogue,
    currentOptions,
    currentScene,
    characterId,
    messages,
    threadId,
  } = gameState.state;

  const lastAssetErrorRef = useRef<{
    composite: string | null;
    scene: string | null;
    character: string | null;
  }>({
    composite: null,
    scene: null,
    character: null,
  });

  useGameTts(currentDialogue, characterId);

  useEffect(() => {
    if (flowState.characterDraft?.voiceConfig) {
      logger.debug('[game] character voice config:', flowState.characterDraft.voiceConfig);
    }
  }, [flowState.characterDraft?.voiceConfig]);

  useEffect(() => {
    actions.scrollToBottom();
    if (!threadId || messages.length === 0) {
      return;
    }

    saveGameProgress(threadId, messages, characterId ?? undefined, derived.persistenceSnapshot);
  }, [
    actions,
    characterId,
    derived.persistenceSnapshot,
    messages,
    saveGameProgress,
    threadId,
  ]);

  const preferredCharacterId = resolvePreferredCharacterId({
    currentCharacterId: characterId,
    activeCharacterId: flowState.runtimeSession.currentCharacterId,
    draftCharacterId: flowState.characterDraft?.characterId,
  });

  const ensureCharacterImage = () => {
    if (characterImageUrl) {
      return;
    }

    setCharacterImage(preferredCharacterId);
  };

  const notifyAssetError = (
    kind: 'composite' | 'scene' | 'character',
    resourceKey: string | null,
    message: string
  ) => {
    const nextKey = resourceKey ?? `${kind}:missing`;
    if (lastAssetErrorRef.current[kind] === nextKey) {
      return;
    }

    lastAssetErrorRef.current[kind] = nextKey;
    feedback.warning(message);
  };

  const applyGameResponse = (responseData: GameTurnResult) => {
    if (responseData.sceneId && responseData.sceneId !== currentScene) {
      actions.enterScene(
        responseData.sceneId,
        resolveSceneDisplayName(responseData.sceneId) ?? responseData.sceneId,
        'advance'
      );
    }

    const visual = resolveStorySceneVisual(responseData);
    if (visual.kind === 'composite') {
      actions.applyCompositeScene(visual.imageUrl);
    } else if (responseData.sceneId || responseData.sceneImageUrl) {
      actions.applySceneVisual({ sceneImageUrl: visual.imageUrl });
      ensureCharacterImage();
    }

    if (responseData.characterDialogue) {
      actions.setDialogue(responseData.characterDialogue);
      actions.appendMessage({
        role: 'assistant',
        content: responseData.characterDialogue,
      });
    }

    actions.setOptions(responseData.playerOptions);

    if (responseData.isGameFinished) {
      feedback.info('游戏结束');
    }
  };

  const recoverExpiredSession = async (): Promise<boolean> => {
    const nextCharacterId = preferredCharacterId;

    if (!nextCharacterId) {
      feedback.error('游戏会话已过期，请返回重新开始游戏');
      return false;
    }

    try {
      const initResponse = await initGame({ game_mode: 'solo', character_id: nextCharacterId });
      const nextThreadId = initResponse.thread_id;

      if (!nextThreadId) {
        feedback.error('游戏会话已过期且无法恢复，请返回重新开始游戏');
        return false;
      }

      actions.setThreadId(nextThreadId);
      setActiveSession({
        threadId: nextThreadId,
        characterId: nextCharacterId,
        initialGameData: null,
      });
      feedback.success('游戏会话已恢复，请重新选择选项');
      return true;
    } catch (error: unknown) {
      logger.error('[game] failed to recover session', error);
      feedback.error('游戏会话已过期且无法恢复，请返回重新开始游戏');
      return false;
    }
  };

  const selectOption = async (optionIndex: number) => {
    if (loading || !threadId) return;

    const selectedOption = currentOptions[optionIndex];
    if (!selectedOption) return;
    const previousDialogue = currentDialogue;
    const previousOptions = currentOptions;

    actions.prepareOptionSelection(selectedOption.text);

    try {
      const response = await processGameInput({
        thread_id: threadId,
        user_input: `option:${optionIndex + 1}`,
        character_id: preferredCharacterId || undefined,
      });

      if (response.threadId && response.threadId !== threadId && preferredCharacterId) {
        actions.setThreadId(response.threadId);
        setActiveSession({
          threadId: response.threadId,
          characterId: preferredCharacterId,
          initialGameData: null,
        });
        feedback.info('游戏会话已恢复');
      }

      applyGameResponse(response);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } }; message?: string };
      const errorMessage = err.response?.data?.message || err.message || '处理选项失败，请稍后重试';

      logger.error('Failed to process game option:', err);

      if (
        errorMessage.includes('会话已过期') ||
        errorMessage.includes('not found') ||
        errorMessage.includes('无法恢复')
      ) {
        feedback.warning('游戏会话已过期，正在尝试恢复...');
        await recoverExpiredSession();
      } else if (errorMessage.includes('timeout') || errorMessage.includes('超时')) {
        feedback.error('处理选项超时，AI 生成可能需要更长时间，请稍后重试');
      } else {
        feedback.error(errorMessage);
      }

      actions.setDialogue(previousDialogue);
      actions.setOptions(previousOptions);
      actions.rollbackPendingUserMessage();
    } finally {
      actions.stopLoading();
    }
  };

  const dismissTransition = () => {
    actions.clearSceneTransition();
  };

  const handleCompositeAssetError = () => {
    const failedCompositeImageUrl = compositeImageUrl;
    actions.markCompositeAssetFailed();
    notifyAssetError(
      'composite',
      failedCompositeImageUrl,
      '合成场景加载失败，已切换为占位背景。建议稍后重试或重新进入当前场景。'
    );
  };

  const handleSceneAssetError = () => {
    const failedSceneImageUrl = sceneImageUrl;
    actions.markSceneAssetFailed();
    notifyAssetError(
      'scene',
      failedSceneImageUrl,
      '场景背景加载失败，已显示占位背景。你可以继续游戏，也可以稍后重试。'
    );
  };

  const handleCharacterAssetError = () => {
    const failedCharacterImageUrl = characterImageUrl;
    actions.markCharacterAssetFailed();
    notifyAssetError(
      'character',
      failedCharacterImageUrl,
      '角色立绘加载失败，当前将隐藏角色图层并继续游戏。'
    );
  };

  return {
    actNumber,
    showTransition,
    transitionSceneName,
    loading,
    shouldUseComposite,
    compositeImageUrl,
    sceneImageUrl,
    characterImageUrl,
    currentDialogue,
    currentOptions,
    dismissTransition,
    handleCharacterAssetError,
    handleCompositeAssetError,
    handleSceneAssetError,
    selectOption,
  };
}
