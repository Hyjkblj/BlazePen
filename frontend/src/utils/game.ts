import type { CharacterData } from '@/types/game';

export function resolveCharacterImageUrl(
  characterData?: CharacterData | null
): string | undefined {
  if (!characterData) return undefined;
  if (characterData.transparentImageUrl) return characterData.transparentImageUrl;

  const imageUrl = characterData.imageUrl;
  const isDeleted = (url: string) => /portrait_img[123]/.test(url);

  if (
    imageUrl &&
    isDeleted(imageUrl) &&
    characterData.originalImageUrl &&
    !isDeleted(characterData.originalImageUrl)
  ) {
    return characterData.originalImageUrl;
  }

  if (imageUrl && isDeleted(imageUrl)) return undefined;
  return characterData.originalImageUrl || imageUrl;
}
