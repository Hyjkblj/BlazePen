import { describe, expect, it } from 'vitest';
import {
  normalizeInitialGameData,
  normalizeStoryScenePayload,
  resolveSceneImageAsset,
  resolveStorySceneVisual,
  toInitialGameData,
} from './storyScene';

describe('normalizeStoryScenePayload', () => {
  it('converts backend payloads into the frontend story scene model', () => {
    expect(
      normalizeStoryScenePayload({
        scene: ' study_room ',
        scene_image_url: ' /scene.png ',
        composite_image_url: 'undefined',
        story_background: ' Prologue ',
        character_dialogue: '',
        player_options: [{ id: 1, text: 'Continue', type: 'action' }],
        is_game_finished: true,
      })
    ).toEqual({
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: 'Prologue',
      characterDialogue: null,
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
      isGameFinished: true,
    });
  });
});

describe('toInitialGameData', () => {
  it('accepts already-normalized story data without leaking backend-only fields', () => {
    expect(
      toInitialGameData({
        sceneId: 'cafe_nearby',
        sceneImageUrl: '/scene.png',
        compositeImageUrl: null,
        storyBackground: 'Intro',
        characterDialogue: 'Hello there',
        playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
        isGameFinished: true,
      })
    ).toEqual({
      sceneId: 'cafe_nearby',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: 'Intro',
      characterDialogue: 'Hello there',
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
    });
  });
});

describe('normalizeInitialGameData', () => {
  it('supports both camelCase and legacy snake_case persisted snapshots', () => {
    expect(
      normalizeInitialGameData({
        sceneId: 'restaurant',
        storyBackground: 'Intro',
        characterDialogue: 'Hi',
        playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
        compositeImageUrl: null,
        sceneImageUrl: '/scene.png',
      })
    ).toEqual({
      sceneId: 'restaurant',
      storyBackground: 'Intro',
      characterDialogue: 'Hi',
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
      compositeImageUrl: null,
      sceneImageUrl: '/scene.png',
    });

    expect(
      normalizeInitialGameData({
        scene: 'company',
        story_background: 'Backstory',
        character_dialogue: 'Welcome',
        player_options: [{ id: 2, text: 'Enter', type: 'action' }],
        composite_image_url: '/composite.png',
        scene_image_url: '/scene-legacy.png',
      })
    ).toEqual({
      sceneId: 'company',
      storyBackground: 'Backstory',
      characterDialogue: 'Welcome',
      playerOptions: [{ id: 2, text: 'Enter', type: 'action' }],
      compositeImageUrl: '/composite.png',
      sceneImageUrl: '/scene-legacy.png',
    });
  });

  it('returns null for invalid persisted values', () => {
    expect(normalizeInitialGameData(null)).toBeNull();
    expect(normalizeInitialGameData(undefined)).toBeNull();
  });
});

describe('resolveSceneImageAsset', () => {
  it('prefers explicit scene image urls and falls back to config or guessed assets', () => {
    expect(resolveSceneImageAsset('cafe_nearby', '/explicit-scene.png')).toBe('/explicit-scene.png');
    expect(resolveSceneImageAsset('cafe_nearby', null)).toMatch(/^\/static\/images\/scenes\/cafe_nearby_/);
    expect(resolveSceneImageAsset('mystery_room', null)).toBe(
      '/static/images/smallscenes/UNKNOWN_SCENE_mystery_room_mystery_room_scene_v1.jpg'
    );
  });
});

describe('resolveStorySceneVisual', () => {
  it('prioritizes composite imagery over scene imagery', () => {
    expect(
      resolveStorySceneVisual({
        sceneId: 'cafe_nearby',
        sceneImageUrl: '/scene.png',
        compositeImageUrl: '/composite.png',
      })
    ).toEqual({
      kind: 'composite',
      imageUrl: '/composite.png',
    });

    expect(
      resolveStorySceneVisual({
        sceneId: 'study_room',
        sceneImageUrl: null,
        compositeImageUrl: null,
      })
    ).toEqual({
      kind: 'scene',
      imageUrl: expect.stringMatching(/^\/static\/images\/scenes\/study_room_/),
    });
  });
});
