import { getSceneConfig, getSceneNameById } from '@/config/scenes';

const DEFAULT_SCENE_IMAGE_EXTENSION = '.jpeg';

export function buildStaticSceneImageUrl(
  sceneId: string,
  sceneName: string,
  extension: string = DEFAULT_SCENE_IMAGE_EXTENSION
): string {
  return `/static/images/scenes/${sceneId}_${encodeURIComponent(sceneName)}${extension}`;
}

export function buildUnknownSceneImageUrl(sceneId: string, sceneName: string): string {
  return `/static/images/smallscenes/UNKNOWN_SCENE_${sceneId}_${encodeURIComponent(sceneName)}_scene_v1.jpg`;
}

export function resolveStaticSceneImageFallback(sceneId: string | null): string | null {
  if (!sceneId) {
    return null;
  }

  const sceneConfig = getSceneConfig(sceneId);
  if (sceneConfig) {
    return buildStaticSceneImageUrl(
      sceneConfig.id,
      sceneConfig.name,
      sceneConfig.imageExtensions?.[0] ?? DEFAULT_SCENE_IMAGE_EXTENSION
    );
  }

  return buildUnknownSceneImageUrl(sceneId, getSceneNameById(sceneId));
}
