import httpClient, {
  getErrorData,
  getErrorMessage,
  getErrorStatus,
  isTimeoutError,
  unwrapApiData,
} from '@/services/httpClient';
import type {
  CharacterImagesResponse,
  CreateCharacterRequest,
  CreateCharacterResponse,
  GenericApiRecord,
  GetScenesResponse,
  InitializeStoryResponse,
  RemoveBackgroundResponse,
} from '@/types/api';
import type { StorySceneData } from '@/types/game';
import { normalizeStoryScenePayload } from '@/utils/storyScene';
import { logger } from '@/utils/logger';

export const createCharacter = async (
  data: CreateCharacterRequest
): Promise<CreateCharacterResponse> => {
  try {
    const response = await httpClient.post('/v1/characters/create', data, { timeout: 180000 });
    return unwrapApiData<CreateCharacterResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) {
      throw new Error('Character creation timed out. Please retry in a moment.');
    }
    throw error;
  }
};

export const getCharacter = async (characterId: string): Promise<GenericApiRecord> => {
  const response = await httpClient.get(`/v1/characters/${characterId}`);
  return unwrapApiData<GenericApiRecord>(response);
};

export const getCharacterImages = async (
  characterId: string
): Promise<CharacterImagesResponse> => {
  try {
    const response = await httpClient.get(`/v1/characters/${characterId}/images`, {
      timeout: 60000,
    });
    return unwrapApiData<CharacterImagesResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) {
      logger.warn('Character image fetch timed out.');
    }
    throw error;
  }
};

export const removeCharacterBackground = async (
  characterId: string,
  imageUrl?: string,
  imageUrls?: string[],
  selectedIndex?: number
): Promise<RemoveBackgroundResponse> => {
  try {
    const response = await httpClient.post(
      `/v1/characters/${characterId}/remove-background`,
      {
        image_url: imageUrl,
        image_urls: imageUrls,
        selected_index: selectedIndex,
      },
      { timeout: 60000 }
    );
    return unwrapApiData<RemoveBackgroundResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) {
      throw new Error('Background removal timed out. Please retry.');
    }
    throw error;
  }
};

export const initializeStory = async (
  threadId: string,
  characterId: string,
  sceneId?: string,
  characterImageUrl?: string
): Promise<StorySceneData> => {
  try {
    if (!threadId || !characterId) {
      throw new Error(`Missing required params: threadId=${threadId}, characterId=${characterId}`);
    }

    const response = await httpClient.post(
      '/v1/characters/initialize-story',
      {
        thread_id: threadId,
        character_id: String(characterId),
        scene_id: sceneId || 'school',
        character_image_url: characterImageUrl || undefined,
      },
      { timeout: 60000 }
    );
    return normalizeStoryScenePayload(unwrapApiData<InitializeStoryResponse>(response));
  } catch (error: unknown) {
    if (getErrorStatus(error) === 422) {
      const errorData = getErrorData(error);
      const detail = errorData?.detail || errorData?.message || 'Invalid request parameters.';
      throw new Error(`Request validation failed: ${JSON.stringify(detail)}`);
    }
    if (isTimeoutError(error)) {
      throw new Error('Story initialization timed out. Please retry.');
    }
    throw error;
  }
};

export const getScenes = async (): Promise<GetScenesResponse> => {
  try {
    const response = await httpClient.get('/v1/characters/scenes');
    return unwrapApiData<GetScenesResponse>(response);
  } catch (error: unknown) {
    logger.error('Failed to fetch scenes:', {
      status: getErrorStatus(error),
      data: getErrorData(error),
      message: getErrorMessage(error),
    });
    throw error;
  }
};
