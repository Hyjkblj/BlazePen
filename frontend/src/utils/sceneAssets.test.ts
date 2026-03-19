import { describe, expect, it } from 'vitest';
import {
  buildStaticSceneImageUrl,
  buildUnknownSceneImageUrl,
  resolveStaticSceneImageFallback,
} from './sceneAssets';

describe('buildStaticSceneImageUrl', () => {
  it('encodes the scene name when building known static asset urls', () => {
    expect(buildStaticSceneImageUrl('cafe_nearby', '咖啡厅')).toBe(
      '/static/images/scenes/cafe_nearby_%E5%92%96%E5%95%A1%E5%8E%85.jpeg'
    );
  });
});

describe('buildUnknownSceneImageUrl', () => {
  it('builds the minimal unknown-scene fallback asset path', () => {
    expect(buildUnknownSceneImageUrl('mystery_room', 'mystery_room')).toBe(
      '/static/images/smallscenes/UNKNOWN_SCENE_mystery_room_mystery_room_scene_v1.jpg'
    );
  });
});

describe('resolveStaticSceneImageFallback', () => {
  it('returns the preferred known scene asset when the scene exists in the display catalog', () => {
    expect(resolveStaticSceneImageFallback('study_room')).toBe(
      '/static/images/scenes/study_room_%E8%87%AA%E4%B9%A0%E5%AE%A4.jpeg'
    );
  });

  it('falls back to the unknown-scene asset naming convention for uncatalogued scenes', () => {
    expect(resolveStaticSceneImageFallback('mystery_room')).toBe(
      '/static/images/smallscenes/UNKNOWN_SCENE_mystery_room_mystery_room_scene_v1.jpg'
    );
    expect(resolveStaticSceneImageFallback(null)).toBeNull();
  });
});
