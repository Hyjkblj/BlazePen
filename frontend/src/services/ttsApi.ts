import httpClient, { getErrorMessage, isTimeoutError, unwrapApiData } from '@/services/httpClient';
import type {
  GenerateSpeechOptions,
  GenerateSpeechResponse,
  GenericApiRecord,
  PresetVoiceItem,
  PresetVoicesResponse,
  SetVoiceConfigRequest,
  VoicePreviewResponse,
} from '@/types/api';
import { logger } from '@/utils/logger';

export const getPresetVoices = async (gender?: string): Promise<PresetVoiceItem[]> => {
  try {
    const response = await httpClient.get(
      '/v1/tts/presets',
      gender ? { params: { gender } } : undefined
    );
    const payload = unwrapApiData<PresetVoicesResponse>(response);
    const voices = payload?.voices;

    if (Array.isArray(voices)) {
      return voices;
    }

    if (voices && typeof voices === 'object') {
      return [...(voices.female || []), ...(voices.male || []), ...(voices.neutral || [])];
    }

    return [];
  } catch (error: unknown) {
    logger.error('Failed to fetch preset voices:', error);
    throw error;
  }
};

export const generateSpeech = async (
  text: string,
  characterId: number | string,
  options?: GenerateSpeechOptions
): Promise<GenerateSpeechResponse | null> => {
  try {
    const characterIdNum = typeof characterId === 'string' ? parseInt(characterId, 10) : characterId;
    if (Number.isNaN(characterIdNum)) {
      throw new Error('Invalid character_id');
    }

    const response = await httpClient.post('/v1/tts/generate', {
      text: text.slice(0, 600),
      character_id: characterIdNum,
      use_cache: options?.use_cache ?? true,
      emotion_params: options?.emotion_params,
    });
    return unwrapApiData<GenerateSpeechResponse>(response);
  } catch (error: unknown) {
    logger.warn('TTS generation failed:', getErrorMessage(error));
    return null;
  }
};

export const getVoicePreviewAudio = async (
  presetVoiceId: string,
  text?: string
): Promise<VoicePreviewResponse | null> => {
  try {
    const response = await httpClient.post(
      '/v1/tts/preview',
      {
        preset_voice_id: presetVoiceId,
        text: text || undefined,
      },
      { timeout: 45000 }
    );
    return unwrapApiData<VoicePreviewResponse>(response);
  } catch (error: unknown) {
    logger.warn('Voice preview failed:', getErrorMessage(error));
    if (isTimeoutError(error)) {
      logger.warn('Voice preview timed out.');
    }
    return null;
  }
};

export const setVoiceConfig = async (
  params: SetVoiceConfigRequest
): Promise<GenericApiRecord> => {
  const response = await httpClient.post('/v1/tts/voice/config', params);
  return unwrapApiData<GenericApiRecord>(response);
};
