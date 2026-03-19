import { useCallback, useEffect, useRef, useState } from 'react';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { getStaticAssetUrl } from '@/services/assetUrl';
import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';
import { getPresetVoices, getVoicePreviewAudio, setVoiceConfig } from '@/services/ttsApi';
import type { PresetVoiceItem } from '@/types/api';
import type { CharacterVoiceConfig } from '@/types/game';
import { logger } from '@/utils/logger';

export interface UseCharacterVoiceSelectionOptions {
  enabled: boolean;
  feedback: Pick<FeedbackContextValue, 'error' | 'warning'>;
  initialSelectedVoiceId: string | null;
}

export interface UseCharacterVoiceSelectionResult {
  presetVoices: PresetVoiceItem[];
  selectedVoiceId: string | null;
  voicesLoading: boolean;
  previewingVoiceId: string | null;
  selectVoice: (voiceId: string) => void;
  previewVoice: (voice: PresetVoiceItem) => Promise<void>;
  persistSelectedVoiceConfig: (characterId: string) => Promise<CharacterVoicePersistResult>;
  resetVoicePreview: () => void;
}

export type CharacterVoicePersistResult =
  | {
      status: 'skipped';
    }
  | {
      status: 'saved';
      voiceConfig: CharacterVoiceConfig;
    }
  | {
      status: 'failed';
      error: unknown;
    };

export function useCharacterVoiceSelection({
  enabled,
  feedback,
  initialSelectedVoiceId,
}: UseCharacterVoiceSelectionOptions): UseCharacterVoiceSelectionResult {
  const [presetVoices, setPresetVoices] = useState<PresetVoiceItem[]>([]);
  const [selectedVoiceId, setSelectedVoiceId] = useState<string | null>(
    initialSelectedVoiceId ?? null
  );
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewRequestIdRef = useRef(0);

  const stopPreviewAudio = useCallback(() => {
    const activeAudio = previewAudioRef.current;
    if (!activeAudio) {
      return;
    }

    activeAudio.pause();
    activeAudio.currentTime = 0;
    activeAudio.onended = null;
    activeAudio.onerror = null;
    previewAudioRef.current = null;
  }, []);

  const resetVoicePreview = useCallback(() => {
    previewRequestIdRef.current += 1;
    stopPreviewAudio();
    setPreviewingVoiceId(null);
  }, [stopPreviewAudio]);

  useEffect(() => {
    setSelectedVoiceId(initialSelectedVoiceId ?? null);
  }, [initialSelectedVoiceId]);

  useEffect(() => {
    return () => {
      resetVoicePreview();
    };
  }, [resetVoicePreview]);

  useEffect(() => {
    if (!enabled) {
      resetVoicePreview();
      return;
    }

    let cancelled = false;
    setVoicesLoading(true);

    void getPresetVoices()
      .then((voices) => {
        if (cancelled) {
          return;
        }

        setPresetVoices(voices);
        if (voices.length === 0) {
          feedback.warning('未获取到音色列表，请检查后端服务。');
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
          feedback.warning('TTS 服务暂不可用，但您仍可选择音色。');
        } else {
          feedback.error(getServiceErrorMessage(error, '获取音色列表失败，请检查后端服务。'));
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
  }, [enabled, feedback, resetVoicePreview]);

  const selectVoice = useCallback((voiceId: string) => {
    setSelectedVoiceId(voiceId);
  }, []);

  const previewVoice = useCallback(
    async (voice: PresetVoiceItem) => {
      previewRequestIdRef.current += 1;
      const requestId = previewRequestIdRef.current;

      stopPreviewAudio();
      setPreviewingVoiceId(voice.id);

      try {
        const result = await getVoicePreviewAudio(voice.id, voice.preview_text || undefined);
        if (previewRequestIdRef.current !== requestId) {
          return;
        }

        if (!result?.audio_url) {
          feedback.warning('试听功能暂不可用，但您仍可选择此音色。');
          return;
        }

        const audio = new Audio(getStaticAssetUrl(result.audio_url));
        previewAudioRef.current = audio;

        audio.onended = () => {
          if (previewAudioRef.current === audio) {
            previewAudioRef.current = null;
          }
          if (previewRequestIdRef.current === requestId) {
            setPreviewingVoiceId(null);
          }
        };

        audio.onerror = () => {
          if (previewAudioRef.current === audio) {
            previewAudioRef.current = null;
          }
          if (previewRequestIdRef.current === requestId) {
            setPreviewingVoiceId(null);
          }
          feedback.warning('试听音频播放失败。');
        };

        try {
          await audio.play();
        } catch {
          if (previewAudioRef.current === audio) {
            previewAudioRef.current = null;
          }
          if (previewRequestIdRef.current === requestId) {
            setPreviewingVoiceId(null);
          }
          feedback.warning('试听音频播放失败。');
        }
      } catch (error: unknown) {
        logger.warn('[character-selection] voice preview failed', error);
        feedback.warning('试听失败，但您仍可选择此音色。');
      } finally {
        if (previewRequestIdRef.current === requestId && !previewAudioRef.current) {
          setPreviewingVoiceId(null);
        }
      }
    },
    [feedback, stopPreviewAudio]
  );

  const persistSelectedVoiceConfig = useCallback(
    async (characterId: string): Promise<CharacterVoicePersistResult> => {
      if (!selectedVoiceId) {
        return {
          status: 'skipped',
        };
      }

      const numericCharacterId = Number(characterId);
      if (Number.isNaN(numericCharacterId)) {
        logger.warn('[character-selection] invalid character id for voice config', characterId);
        return {
          status: 'failed',
          error: new Error('Invalid character id for voice config.'),
        };
      }

      try {
        await setVoiceConfig({
          character_id: numericCharacterId,
          voice_type: 'preset',
          preset_voice_id: selectedVoiceId,
        });

        const selectedVoice = presetVoices.find((voiceItem) => voiceItem.id === selectedVoiceId);
        return {
          status: 'saved',
          voiceConfig: {
            voice_type: 'preset',
            preset_voice_id: selectedVoiceId,
            voice_name: selectedVoice?.name || '未知音色',
            voice_description: selectedVoice?.description || '',
            voice_id: selectedVoice?.voice_id || '',
          },
        };
      } catch (error: unknown) {
        logger.warn('[character-selection] failed to persist voice config', error);
        return {
          status: 'failed',
          error,
        };
      }
    },
    [presetVoices, selectedVoiceId]
  );

  return {
    presetVoices,
    selectedVoiceId,
    voicesLoading,
    previewingVoiceId,
    selectVoice,
    previewVoice,
    persistSelectedVoiceConfig,
    resetVoicePreview,
  };
}
