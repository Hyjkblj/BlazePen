import { getSceneNameById } from '@/config/scenes';
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

export function getFallbackSceneImageUrls(sceneId: string): string[] {
  const sceneName = getSceneNameById(sceneId);
  const encoded = encodeURIComponent(sceneName);

  return [
    `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encoded}_scene_v1.jpg`,
    `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encoded}_scene_v1.jpeg`,
    `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encoded}_scene_v1.png`,
    `/static/images/scenes/${sceneId}_${encoded}.jpeg`,
    `/static/images/scenes/${sceneId}_${encoded}.jpg`,
    `/static/images/scenes/${sceneId}_${encoded}.png`,
  ];
}
