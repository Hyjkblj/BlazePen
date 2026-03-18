import { useEffect } from 'react';
import { useFeedback, useGameFlow } from '@/contexts';
import { useGameInit, useGameState, useGameTts } from '@/hooks';
import { SCENE_CONFIGS, buildSceneImageUrl, getSceneImageUrl, getSceneNameById } from '@/config/scenes';
import { initGame, processGameInput } from '@/services/gameApi';
import type { ProcessGameInputResponse } from '@/types/api';
import type { GameSessionSnapshot, PlayerOption } from '@/types/game';
import { getFallbackSceneImageUrls } from '@/utils/game';
import { logger } from '@/utils/logger';

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
  selectOption: (optionIndex: number) => Promise<void>;
}

export function useGameSessionFlow(): UseGameSessionFlowResult {
  const feedback = useFeedback();
  const { state: flowState, setActiveSession } = useGameFlow();
  const gameState = useGameState();
  const { saveGameProgress, setCharacterImage } = useGameInit(gameState);

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
  const { actions } = gameState;

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

    const snapshot: GameSessionSnapshot = {
      currentDialogue,
      currentOptions,
      currentScene,
      sceneImageUrl,
      characterImageUrl,
      compositeImageUrl,
      shouldUseComposite,
    };

    saveGameProgress(threadId, messages, characterId ?? undefined, snapshot);
  }, [
    actions,
    characterId,
    characterImageUrl,
    compositeImageUrl,
    currentDialogue,
    currentOptions,
    currentScene,
    messages,
    saveGameProgress,
    sceneImageUrl,
    shouldUseComposite,
    threadId,
  ]);

  const ensureCharacterImage = () => {
    if (characterImageUrl) {
      return;
    }

    setCharacterImage(
      characterId ||
        flowState.runtimeSession.currentCharacterId ||
        flowState.characterDraft?.characterId ||
        null
    );
  };

  const resolveSceneImage = (sceneId: string) => {
    const sceneConfig = SCENE_CONFIGS.find((scene) => scene.id === sceneId);

    if (!sceneConfig) {
      return getFallbackSceneImageUrls(sceneId)[0];
    }

    const sceneUrl = getSceneImageUrl(sceneConfig);
    if (sceneUrl) {
      return sceneUrl;
    }

    const ext = sceneConfig.imageExtensions?.[0] ?? '.jpeg';
    return buildSceneImageUrl(sceneConfig.id, sceneConfig.name, ext);
  };

  const applyGameResponse = (responseData: ProcessGameInputResponse) => {
    if (responseData.scene && responseData.scene !== currentScene) {
      actions.enterScene(responseData.scene, getSceneNameById(responseData.scene), 'advance');
    }

    if (responseData.composite_image_url) {
      actions.applyCompositeScene(responseData.composite_image_url);
    } else if (responseData.scene_image_url) {
      actions.applySceneVisual({ sceneImageUrl: responseData.scene_image_url });
      ensureCharacterImage();
    } else if (responseData.scene) {
      actions.applySceneVisual({ sceneImageUrl: resolveSceneImage(responseData.scene) });
      ensureCharacterImage();
    }

    if (responseData.character_dialogue) {
      actions.setDialogue(responseData.character_dialogue);
      actions.appendMessage({
        role: 'assistant',
        content: responseData.character_dialogue,
      });
    }

    actions.setOptions(responseData.player_options);

    if (responseData.is_game_finished) {
      feedback.info('游戏结束');
    }
  };

  const recoverExpiredSession = async (): Promise<boolean> => {
    const nextCharacterId =
      characterId || flowState.runtimeSession.currentCharacterId || flowState.characterDraft?.characterId;

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

    actions.prepareOptionSelection(selectedOption.text);

    try {
      const currentCharacterId =
        characterId || flowState.runtimeSession.currentCharacterId || flowState.characterDraft?.characterId;

      const response = await processGameInput({
        thread_id: threadId,
        user_input: `option:${optionIndex + 1}`,
        character_id: currentCharacterId || undefined,
      });

      if (response.thread_id && response.thread_id !== threadId && currentCharacterId) {
        actions.setThreadId(response.thread_id);
        setActiveSession({
          threadId: response.thread_id,
          characterId: currentCharacterId,
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

      actions.rollbackPendingUserMessage();
    } finally {
      actions.stopLoading();
    }
  };

  const dismissTransition = () => {
    actions.clearSceneTransition();
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
    selectOption,
  };
}

