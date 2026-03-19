import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import {
  useCharacterPortraitSelection,
  useCharacterVoiceSelection,
  type CharacterOption,
} from '@/hooks';
import { checkServerHealth } from '@/services/healthApi';
import { isServiceError } from '@/services/serviceError';
import type { PresetVoiceItem } from '@/types/api';
import { logger } from '@/utils/logger';

export type CharacterSelectionStep = 'image' | 'voice';

export interface UseCharacterSelectionFlowResult {
  loading: boolean;
  loadingMessage: string;
  characters: CharacterOption[];
  selectedCharacter: string | null;
  selectedImageIndex: number | null;
  step: CharacterSelectionStep;
  presetVoices: PresetVoiceItem[];
  selectedVoiceId: string | null;
  voicesLoading: boolean;
  previewingVoiceId: string | null;
  selectedImageUrlForVoice?: string;
  selectImage: (characterId: string, imageIndex: number) => void;
  selectVoice: (voiceId: string) => void;
  previewVoice: (voice: PresetVoiceItem) => Promise<void>;
  confirmVoice: () => Promise<void>;
  backToImageStep: () => void;
}

const delay = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const resolveVoiceSaveFailureMessage = (error: unknown) => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return '音色保存超时，请重试。';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return 'TTS 服务暂不可用，音色尚未保存，请稍后重试。';
  }

  return '音色保存失败，请重试。';
};

export function useCharacterSelectionFlow(): UseCharacterSelectionFlowResult {
  const navigate = useNavigate();
  const feedback = useFeedback();
  const { state, setCharacterDraft, setCreatedCharacterId, updateCharacterDraft } = useGameFlow();

  const [submitting, setSubmitting] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在加载角色...');
  const [step, setStep] = useState<CharacterSelectionStep>('image');

  const portraitSelection = useCharacterPortraitSelection({
    characterDraft: state.characterDraft,
    createdCharacterId: state.createdCharacterId,
    updateCharacterDraft,
  });
  const voiceSelection = useCharacterVoiceSelection({
    enabled: step === 'voice',
    feedback,
    initialSelectedVoiceId: state.characterDraft?.voiceConfig?.preset_voice_id ?? null,
  });

  useEffect(() => {
    let cancelled = false;
    setLoadingMessage('正在加载角色...');

    void portraitSelection.loadCharacters().then((result) => {
      if (cancelled) {
        return;
      }

      switch (result.status) {
        case 'missing-draft':
          feedback.warning('未找到角色数据，请先创建角色。');
          window.setTimeout(() => navigate(ROUTES.CHARACTER_SETTING), 1500);
          break;
        case 'invalid-character-id':
          setCharacterDraft(null);
          setCreatedCharacterId(null);
          feedback.error('角色数据无效，请重新创建角色。');
          break;
        case 'failed':
          feedback.error('加载角色失败，请稍后重试。');
          break;
        case 'loaded':
        default:
          break;
      }
    });

    return () => {
      cancelled = true;
    };
  }, [
    feedback,
    navigate,
    portraitSelection.loadCharacters,
    setCharacterDraft,
    setCreatedCharacterId,
  ]);

  const loading = portraitSelection.loading || submitting;

  const selectImage = (characterId: string, imageIndex: number) => {
    const didSelect = portraitSelection.selectImage(characterId, imageIndex);
    if (!didSelect) {
      feedback.warning('图片数据异常，请刷新页面重试。');
      return;
    }

    setStep('voice');
  };

  const confirmVoice = async () => {
    const character = portraitSelection.selectedCharacterOption;
    const characterId = character?.id;
    const characterData = state.characterDraft;

    if (!character || !characterId || !characterData) {
      feedback.error('角色数据异常。');
      return;
    }

    setSubmitting(true);
    setLoadingMessage('正在检查服务器连接...');

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        feedback.error('无法连接到服务器，请检查后端服务是否正在运行。');
        return;
      }

      setLoadingMessage('正在保存选择...');

      let nextCharacterData = characterData;

      try {
        nextCharacterData = await portraitSelection.prepareSelectedPortrait(characterData);
      } catch (error: unknown) {
        logger.error('Failed to confirm character selection:', error);
        feedback.warning('选择图片失败，将使用原图继续。');
      }

      const voicePersistResult = await voiceSelection.persistSelectedVoiceConfig(characterId);

      if (voicePersistResult.status === 'failed') {
        setCharacterDraft(nextCharacterData);
        feedback.error(resolveVoiceSaveFailureMessage(voicePersistResult.error));
        return;
      }

      if (voicePersistResult.status === 'saved') {
        nextCharacterData = {
          ...nextCharacterData,
          voiceConfig: voicePersistResult.voiceConfig,
        };
      }

      setCharacterDraft(nextCharacterData);

      setLoadingMessage('选择完成，正在跳转...');
      await delay(500);
      navigate(ROUTES.FIRST_MEETING);
    } catch (error: unknown) {
      logger.error('Failed to submit character selection:', error);
      feedback.error('选择角色失败，请稍后重试。');
    } finally {
      setSubmitting(false);
    }
  };

  const backToImageStep = () => {
    voiceSelection.resetVoicePreview();
    setStep('image');
  };

  return {
    loading,
    loadingMessage,
    characters: portraitSelection.characters,
    selectedCharacter: portraitSelection.selectedCharacter,
    selectedImageIndex: portraitSelection.selectedImageIndex,
    step,
    presetVoices: voiceSelection.presetVoices,
    selectedVoiceId: voiceSelection.selectedVoiceId,
    voicesLoading: voiceSelection.voicesLoading,
    previewingVoiceId: voiceSelection.previewingVoiceId,
    selectedImageUrlForVoice: portraitSelection.selectedImageUrlForVoice,
    selectImage,
    selectVoice: voiceSelection.selectVoice,
    previewVoice: voiceSelection.previewVoice,
    confirmVoice,
    backToImageStep,
  };
}
