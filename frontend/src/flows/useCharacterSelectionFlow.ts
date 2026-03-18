import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import { getCharacterImages, removeCharacterBackground } from '@/services/characterApi';
import { checkServerHealth } from '@/services/healthApi';
import { getPresetVoices, getVoicePreviewAudio, setVoiceConfig } from '@/services/ttsApi';
import type { PresetVoiceItem, RemoveBackgroundResponse } from '@/types/api';
import type { CharacterData, CharacterVoiceConfig } from '@/types/game';
import { logger } from '@/utils/logger';

export interface CharacterOption {
  id: string;
  name: string;
  imageUrl?: string;
  imageUrls?: string[];
  gender: 'male' | 'female';
}

export type CharacterSelectionStep = 'image' | 'voice';

interface RemoveBackgroundResultPayload extends RemoveBackgroundResponse {
  data?: Partial<RemoveBackgroundResponse>;
}

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

const deletedPortraitPattern = /portrait_img[123]/;

const isValidStoredId = (value: unknown): value is string | number =>
  value !== undefined &&
  value !== null &&
  value !== 'undefined' &&
  value !== 'null' &&
  String(value).trim() !== '';

const delay = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const resolvePreviewAudioUrl = (audioUrl: string) =>
  audioUrl.startsWith('http') ? audioUrl : `${window.location.origin}${audioUrl}`;

const hasDeletedPortraitImages = (imageUrls: string[]) =>
  imageUrls.some((url) => Boolean(url && deletedPortraitPattern.test(url)));

export function useCharacterSelectionFlow(): UseCharacterSelectionFlowResult {
  const navigate = useNavigate();
  const feedback = useFeedback();
  const { state, setCharacterDraft, setCreatedCharacterId, updateCharacterDraft } = useGameFlow();

  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在加载角色...');
  const [characters, setCharacters] = useState<CharacterOption[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [step, setStep] = useState<CharacterSelectionStep>('image');
  const [presetVoices, setPresetVoices] = useState<PresetVoiceItem[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(
    state.characterDraft?.voiceConfig?.preset_voice_id ?? null
  );
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);

  const loadCharacters = useCallback(async () => {
    setLoading(true);
    setLoadingMessage('正在加载角色...');

    try {
      const characterData = state.characterDraft;
      const createdCharacterId = state.createdCharacterId || characterData?.characterId;

      if (!characterData) {
        feedback.warning('未找到角色数据，请先创建角色');
        window.setTimeout(() => navigate(ROUTES.CHARACTER_SETTING), 1500);
        return;
      }

      if (!isValidStoredId(createdCharacterId)) {
        setCharacterDraft(null);
        setCreatedCharacterId(null);
        feedback.error('角色数据无效，请重新创建角色');
        return;
      }

      const normalizedCharacterId = String(createdCharacterId);
      let imageUrls = characterData.image_urls || [];

      if (characterData.transparentImageUrl && hasDeletedPortraitImages(imageUrls)) {
        imageUrls = [characterData.transparentImageUrl];
        updateCharacterDraft((current) =>
          current
            ? {
                ...current,
                image_urls: imageUrls,
                imageUrl: characterData.transparentImageUrl,
              }
            : current
        );
      }

      const characterOptions: CharacterOption[] = [
        {
          id: normalizedCharacterId,
          name: characterData.name || '角色1',
          imageUrl: characterData.transparentImageUrl || characterData.imageUrl,
          imageUrls,
          gender: characterData.gender === 'male' ? 'male' : 'female',
        },
      ];

      for (const character of characterOptions) {
        if (!isValidStoredId(character.id)) {
          logger.warn('[character-selection] invalid character id, skip image load', character);
          continue;
        }

        if (character.imageUrls && character.imageUrls.length > 0) {
          character.imageUrl = character.imageUrls[0];
          continue;
        }

        try {
          const imagesResponse = await getCharacterImages(character.id);
          if (imagesResponse.images?.length) {
            character.imageUrl = imagesResponse.images[0];
          }
        } catch (error: unknown) {
          logger.warn(`[character-selection] failed to load images for ${character.id}`, error);
        }
      }

      setSelectedCharacter(characterData.selectedCharacterId || normalizedCharacterId);
      setSelectedImageIndex(characterData.selectedImageIndex ?? null);
      setSelectedVoiceId(characterData.voiceConfig?.preset_voice_id ?? null);
      setCharacters(characterOptions);
    } catch (error: unknown) {
      logger.error('Failed to load characters:', error);
      feedback.error('加载角色失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, [feedback, navigate, setCharacterDraft, setCreatedCharacterId, state, updateCharacterDraft]);

  useEffect(() => {
    void loadCharacters();
  }, [loadCharacters]);

  useEffect(() => {
    if (step !== 'voice') return;

    let cancelled = false;
    setVoicesLoading(true);

    void getPresetVoices()
      .then((voices) => {
        if (cancelled) return;
        setPresetVoices(voices);
        if (voices.length === 0) {
          feedback.warning('未获取到音色列表，请检查后端服务');
        }
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const err = error as { response?: { status?: number } };
        if (err.response?.status === 503) {
          feedback.warning('TTS 服务暂不可用，但您仍可选择音色');
        } else {
          feedback.error('获取音色列表失败，请检查后端服务');
        }
        setPresetVoices([]);
      })
      .finally(() => {
        if (!cancelled) {
          setVoicesLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [feedback, step]);

  const selectImage = (characterId: string, imageIndex: number) => {
    const character = characters.find((item) => item.id === characterId);
    if (!character) {
      logger.warn('[character-selection] character not found', characterId);
      return;
    }

    const selectedImageUrl = character.imageUrls?.[imageIndex];
    if (!selectedImageUrl && !character.imageUrl) {
      feedback.warning('图片数据异常，请刷新页面重试');
      return;
    }

    const urlToSave = selectedImageUrl || character.imageUrl;
    setSelectedCharacter(characterId);
    setSelectedImageIndex(imageIndex);

    if (urlToSave) {
      updateCharacterDraft((current) =>
        current
          ? {
              ...current,
              selectedCharacterId: characterId,
              imageUrl: urlToSave,
              selectedImageIndex: imageIndex,
            }
          : current
      );
    }

    setStep('voice');
  };

  const selectVoice = (voiceId: string) => {
    setSelectedVoiceId(voiceId);
  };

  const previewVoice = async (voice: PresetVoiceItem) => {
    if (previewingVoiceId) return;

    setPreviewingVoiceId(voice.id);

    try {
      const result = await getVoicePreviewAudio(voice.id, voice.preview_text || undefined);
      if (!result?.audio_url) {
        feedback.warning('试听功能暂不可用，但您仍可选择此音色');
        return;
      }

      const audio = new Audio(resolvePreviewAudioUrl(result.audio_url));
      audio.onended = () => setPreviewingVoiceId(null);
      audio.onerror = () => {
        setPreviewingVoiceId(null);
        feedback.warning('试听音频播放失败');
      };

      try {
        await audio.play();
      } catch {
        setPreviewingVoiceId(null);
        feedback.warning('试听音频播放失败');
      }
    } catch (error: unknown) {
      const err = error as {
        response?: { status?: number; data?: { message?: string } };
        message?: string;
      };
      const errorMsg = err.response?.data?.message || err.message || '试听失败';

      if (err.response?.status === 503) {
        feedback.warning(`${errorMsg}。您仍可选择此音色，游戏中使用时请确保 TTS 服务已启用。`);
      } else {
        feedback.warning(`试听失败：${errorMsg}`);
      }
    } finally {
      setPreviewingVoiceId(null);
    }
  };

  const confirmVoice = async () => {
    const character = characters[0];
    const characterId = character?.id;
    const characterData = state.characterDraft;

    if (!character || !characterId || !characterData) {
      feedback.error('角色数据异常');
      return;
    }

    const imageIndex = selectedImageIndex ?? 0;
    const selectedImageUrl = character.imageUrls?.[imageIndex] ?? character.imageUrl;

    setLoading(true);
    setLoadingMessage('正在检查服务器连接...');

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        feedback.error('无法连接到服务器，请检查后端服务是否运行');
        return;
      }

      setLoadingMessage('正在保存选择...');

      try {
        const selectionResponse = (await removeCharacterBackground(
          characterId,
          selectedImageUrl,
          character.imageUrls || [],
          imageIndex
        )) as RemoveBackgroundResultPayload;

        const nextCharacterData: CharacterData = { ...characterData };
        const transparentUrl =
          selectionResponse.transparent_url ?? selectionResponse.data?.transparent_url;
        const selectedUrl =
          selectionResponse.selected_image_url ?? selectionResponse.data?.selected_image_url;

        if (transparentUrl) {
          nextCharacterData.transparentImageUrl = transparentUrl;
          nextCharacterData.imageUrl = transparentUrl;
          nextCharacterData.image_urls = [transparentUrl];
        } else {
          if (selectedUrl) {
            nextCharacterData.selectedImageUrl = selectedUrl;
            nextCharacterData.originalImageUrl = selectedUrl;
          }

          const fallbackUrl = selectedUrl || nextCharacterData.imageUrl;
          if (fallbackUrl) {
            nextCharacterData.imageUrl = fallbackUrl;
            nextCharacterData.image_urls = [fallbackUrl];
          }
        }

        if (selectedVoiceId) {
          try {
            await setVoiceConfig({
              character_id: Number(characterId),
              voice_type: 'preset',
              preset_voice_id: selectedVoiceId,
            });

            const selectedVoice = presetVoices.find((voice) => voice.id === selectedVoiceId);
            const voiceConfig: CharacterVoiceConfig = {
              voice_type: 'preset',
              preset_voice_id: selectedVoiceId,
              voice_name: selectedVoice?.name || '未知音色',
              voice_description: selectedVoice?.description || '',
              voice_id: selectedVoice?.voice_id || '',
            };
            nextCharacterData.voiceConfig = voiceConfig;
          } catch (error: unknown) {
            logger.warn('[character-selection] failed to persist voice config', error);
          }
        }

        setCharacterDraft(nextCharacterData);

        setLoadingMessage('选择完成，正在跳转...');
        await delay(500);
        navigate(ROUTES.FIRST_MEETING);
      } catch (error: unknown) {
        logger.error('Failed to confirm character selection:', error);
        feedback.warning('选择图片失败，将使用原图继续');
        await delay(500);
        navigate(ROUTES.FIRST_MEETING);
      }
    } catch (error: unknown) {
      logger.error('Failed to submit character selection:', error);
      feedback.error('选择角色失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const backToImageStep = () => {
    setStep('image');
  };

  const primaryCharacter = characters[0];
  const selectedImageUrlForVoice =
    primaryCharacter &&
    selectedImageIndex != null &&
    primaryCharacter.imageUrls?.[selectedImageIndex]
      ? primaryCharacter.imageUrls[selectedImageIndex]
      : primaryCharacter?.imageUrl;

  return {
    loading,
    loadingMessage,
    characters,
    selectedCharacter,
    selectedImageIndex,
    step,
    presetVoices,
    selectedVoiceId,
    voicesLoading,
    previewingVoiceId,
    selectedImageUrlForVoice,
    selectImage,
    selectVoice,
    previewVoice,
    confirmVoice,
    backToImageStep,
  };
}
