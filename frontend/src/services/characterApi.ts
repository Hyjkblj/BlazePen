import httpClient, { unwrapApiData } from '@/services/httpClient';
import { toServiceError } from '@/services/serviceError';
import type {
  CharacterImagesResponse,
  CreateCharacterRequest,
  CreateCharacterResponse,
  GenericApiRecord,
  RemoveBackgroundResponse,
} from '@/types/api';
import type { CharacterCreationResult } from '@/types/game';
import { logger } from '@/utils/logger';

const normalizeOptionalString = (value: unknown): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  if (normalized === '' || normalized === 'null' || normalized === 'undefined') {
    return null;
  }

  return normalized;
};

const normalizeCharacterCreationResult = (
  payload: CreateCharacterResponse | null | undefined
): CharacterCreationResult => ({
  characterId:
    normalizeOptionalString(
      typeof payload?.character_id === 'string' || typeof payload?.character_id === 'number'
        ? String(payload.character_id)
        : null
    ) ?? '',
  name: normalizeOptionalString(payload?.name),
  imageUrl: normalizeOptionalString(payload?.image_url),
  imageUrls: Array.isArray(payload?.image_urls)
    ? payload.image_urls.filter(
        (item): item is string => typeof item === 'string' && item.trim() !== ''
      )
    : [],
});

export const createCharacter = async (
  data: CreateCharacterRequest
): Promise<CharacterCreationResult> => {
  try {
    const response = await httpClient.post('/v1/characters/create', data, { timeout: 180000 });
    return normalizeCharacterCreationResult(unwrapApiData<CreateCharacterResponse>(response));
  } catch (error: unknown) {
    throw toServiceError(error, {
      fallbackMessage: 'Failed to create character.',
      timeoutMessage: 'Character creation timed out. Please retry in a moment.',
    });
  }
};

export const getCharacter = async (characterId: string): Promise<GenericApiRecord> => {
  try {
    const response = await httpClient.get(`/v1/characters/${characterId}`);
    return unwrapApiData<GenericApiRecord>(response);
  } catch (error: unknown) {
    throw toServiceError(error, {
      fallbackMessage: 'Failed to load character details.',
    });
  }
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
    const serviceError = toServiceError(error, {
      fallbackMessage: 'Failed to load character images.',
      timeoutMessage: 'Character image fetch timed out. Please retry.',
    });
    logger.warn('[character-api] character image request failed', serviceError);
    throw serviceError;
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
    throw toServiceError(error, {
      fallbackMessage: 'Failed to remove character background.',
      timeoutMessage: 'Background removal timed out. Please retry.',
    });
  }
};
