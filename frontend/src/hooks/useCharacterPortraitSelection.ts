import { useCallback, useMemo, useState } from 'react';
import { getCharacterImages, removeCharacterBackground } from '@/services/characterApi';
import type { RemoveBackgroundResponse } from '@/types/api';
import type { CharacterData } from '@/types/game';
import { logger } from '@/utils/logger';

export interface CharacterOption {
  id: string;
  name: string;
  imageUrl?: string;
  imageUrls?: string[];
  gender: 'male' | 'female';
}

export interface UseCharacterPortraitSelectionOptions {
  characterDraft: CharacterData | null;
  createdCharacterId: string | null;
  updateCharacterDraft: (
    updater: (current: CharacterData | null) => CharacterData | null
  ) => void;
}

export interface CharacterSelectionLoadResult {
  status: 'loaded' | 'missing-draft' | 'invalid-character-id' | 'failed';
  error?: unknown;
}

export interface UseCharacterPortraitSelectionResult {
  loading: boolean;
  characters: CharacterOption[];
  selectedCharacter: string | null;
  selectedCharacterOption: CharacterOption | null;
  selectedImageIndex: number | null;
  selectedImageUrlForVoice?: string;
  loadCharacters: () => Promise<CharacterSelectionLoadResult>;
  selectImage: (characterId: string, imageIndex: number) => boolean;
  prepareSelectedPortrait: (characterData: CharacterData) => Promise<CharacterData>;
}

interface RemoveBackgroundResultPayload extends RemoveBackgroundResponse {
  data?: Partial<RemoveBackgroundResponse>;
}

const deletedPortraitPattern = /portrait_img[123]/;

const isValidStoredId = (value: unknown): value is string | number =>
  value !== undefined &&
  value !== null &&
  value !== 'undefined' &&
  value !== 'null' &&
  String(value).trim() !== '';

const hasDeletedPortraitImages = (imageUrls: string[]) =>
  imageUrls.some((url) => Boolean(url && deletedPortraitPattern.test(url)));

const resolveActiveCharacter = (
  characters: CharacterOption[],
  selectedCharacter: string | null
): CharacterOption | null => {
  if (selectedCharacter) {
    const matchedCharacter = characters.find((item) => item.id === selectedCharacter);
    if (matchedCharacter) {
      return matchedCharacter;
    }
  }

  return characters[0] ?? null;
};

export function useCharacterPortraitSelection({
  characterDraft,
  createdCharacterId,
  updateCharacterDraft,
}: UseCharacterPortraitSelectionOptions): UseCharacterPortraitSelectionResult {
  const [loading, setLoading] = useState(false);
  const [characters, setCharacters] = useState<CharacterOption[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<string | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);

  const loadCharacters = useCallback(async (): Promise<CharacterSelectionLoadResult> => {
    setLoading(true);

    try {
      if (!characterDraft) {
        return { status: 'missing-draft' };
      }

      const resolvedCharacterId = createdCharacterId || characterDraft.characterId;
      if (!isValidStoredId(resolvedCharacterId)) {
        return { status: 'invalid-character-id' };
      }

      const normalizedCharacterId = String(resolvedCharacterId);
      let imageUrls = characterDraft.image_urls || [];

      if (characterDraft.transparentImageUrl && hasDeletedPortraitImages(imageUrls)) {
        imageUrls = [characterDraft.transparentImageUrl];
        updateCharacterDraft((current) =>
          current
            ? {
                ...current,
                image_urls: imageUrls,
                imageUrl: characterDraft.transparentImageUrl,
              }
            : current
        );
      }

      const characterOptions: CharacterOption[] = [
        {
          id: normalizedCharacterId,
          name: characterDraft.name || '角色 1',
          imageUrl: characterDraft.transparentImageUrl || characterDraft.imageUrl,
          imageUrls,
          gender: characterDraft.gender === 'male' ? 'male' : 'female',
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

      setSelectedCharacter(characterDraft.selectedCharacterId || normalizedCharacterId);
      setSelectedImageIndex(characterDraft.selectedImageIndex ?? null);
      setCharacters(characterOptions);

      return { status: 'loaded' };
    } catch (error: unknown) {
      logger.error('Failed to load characters:', error);
      return {
        status: 'failed',
        error,
      };
    } finally {
      setLoading(false);
    }
  }, [characterDraft, createdCharacterId, updateCharacterDraft]);

  const selectImage = useCallback(
    (characterId: string, imageIndex: number) => {
      const character = characters.find((item) => item.id === characterId);
      if (!character) {
        logger.warn('[character-selection] character not found', characterId);
        return false;
      }

      const selectedImageUrl = character.imageUrls?.[imageIndex];
      if (!selectedImageUrl && !character.imageUrl) {
        return false;
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

      return true;
    },
    [characters, updateCharacterDraft]
  );

  const selectedCharacterOption = useMemo(
    () => resolveActiveCharacter(characters, selectedCharacter),
    [characters, selectedCharacter]
  );

  const selectedImageUrlForVoice = useMemo(() => {
    if (!selectedCharacterOption) {
      return undefined;
    }

    if (
      selectedImageIndex != null &&
      selectedCharacterOption.imageUrls?.[selectedImageIndex]
    ) {
      return selectedCharacterOption.imageUrls[selectedImageIndex];
    }

    return selectedCharacterOption.imageUrl;
  }, [selectedCharacterOption, selectedImageIndex]);

  const prepareSelectedPortrait = useCallback(
    async (characterData: CharacterData) => {
      const activeCharacter = resolveActiveCharacter(characters, selectedCharacter);
      if (!activeCharacter?.id) {
        throw new Error('Character selection is unavailable.');
      }

      const imageIndex = selectedImageIndex ?? 0;
      const selectedImageUrl =
        activeCharacter.imageUrls?.[imageIndex] ?? activeCharacter.imageUrl;

      const selectionResponse = (await removeCharacterBackground(
        activeCharacter.id,
        selectedImageUrl,
        activeCharacter.imageUrls || [],
        imageIndex
      )) as RemoveBackgroundResultPayload;

      const nextCharacterData: CharacterData = {
        ...characterData,
        selectedCharacterId: activeCharacter.id,
        selectedImageIndex: imageIndex,
      };
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

      return nextCharacterData;
    },
    [characters, selectedCharacter, selectedImageIndex]
  );

  return {
    loading,
    characters,
    selectedCharacter,
    selectedCharacterOption,
    selectedImageIndex,
    selectedImageUrlForVoice,
    loadCharacters,
    selectImage,
    prepareSelectedPortrait,
  };
}
