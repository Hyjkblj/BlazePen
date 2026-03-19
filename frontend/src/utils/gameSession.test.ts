import { describe, expect, it } from 'vitest';
import {
  buildInitialAssistantMessages,
  hasStorySceneVisual,
  resolvePreferredCharacterId,
  resolveSelectedSceneTransition,
} from './gameSession';

describe('resolvePreferredCharacterId', () => {
  it('prefers the current character id over other fallbacks', () => {
    expect(
      resolvePreferredCharacterId({
        currentCharacterId: ' current-id ',
        activeCharacterId: 'active-id',
        draftCharacterId: 'draft-id',
      })
    ).toBe('current-id');
  });

  it('falls back to the first available character id', () => {
    expect(
      resolvePreferredCharacterId({
        currentCharacterId: null,
        activeCharacterId: 'active-id',
        draftCharacterId: 'draft-id',
      })
    ).toBe('active-id');

    expect(
      resolvePreferredCharacterId({
        currentCharacterId: null,
        activeCharacterId: null,
        draftCharacterId: 'draft-id',
      })
    ).toBe('draft-id');

    expect(resolvePreferredCharacterId({})).toBeNull();
  });

  it('ignores dirty storage sentinel strings and keeps falling back', () => {
    expect(
      resolvePreferredCharacterId({
        currentCharacterId: 'null',
        activeCharacterId: ' undefined ',
        draftCharacterId: 'draft-id',
      })
    ).toBe('draft-id');

    expect(
      resolvePreferredCharacterId({
        currentCharacterId: ' null ',
        activeCharacterId: 'undefined',
        draftCharacterId: '  ',
      })
    ).toBeNull();
  });
});

describe('hasStorySceneVisual', () => {
  it('detects scene visuals from composite, scene image, or scene id', () => {
    expect(
      hasStorySceneVisual({
        sceneId: null,
        sceneImageUrl: null,
        compositeImageUrl: '/composite.png',
        storyBackground: null,
        characterDialogue: null,
      })
    ).toBe(true);

    expect(
      hasStorySceneVisual({
        sceneId: 'cafe_nearby',
        sceneImageUrl: null,
        compositeImageUrl: null,
        storyBackground: null,
        characterDialogue: null,
      })
    ).toBe(true);

    expect(
      hasStorySceneVisual({
        sceneId: null,
        sceneImageUrl: null,
        compositeImageUrl: null,
        storyBackground: 'intro',
        characterDialogue: 'line',
      })
    ).toBe(false);
  });
});

describe('buildInitialAssistantMessages', () => {
  it('builds assistant messages in background-then-dialogue order', () => {
    expect(
      buildInitialAssistantMessages({
        sceneId: null,
        sceneImageUrl: null,
        compositeImageUrl: null,
        storyBackground: 'Story intro',
        characterDialogue: 'Character line',
      })
    ).toEqual([
      { role: 'assistant', content: 'Story intro' },
      { role: 'assistant', content: 'Character line' },
    ]);
  });

  it('omits empty assistant messages', () => {
    expect(
      buildInitialAssistantMessages({
        sceneId: null,
        sceneImageUrl: null,
        compositeImageUrl: null,
        storyBackground: null,
        characterDialogue: 'Only dialogue',
      })
    ).toEqual([{ role: 'assistant', content: 'Only dialogue' }]);
  });
});

describe('resolveSelectedSceneTransition', () => {
  it('returns null when there is no selected scene id', () => {
    expect(resolveSelectedSceneTransition(null, () => null)).toBeNull();
    expect(resolveSelectedSceneTransition({ id: 'undefined' }, () => 'Fallback')).toBeNull();
  });

  it('prefers the selected scene name and falls back to a resolver', () => {
    expect(
      resolveSelectedSceneTransition(
        { id: 'scene-1', name: 'Named scene' },
        () => 'Resolved scene'
      )
    ).toEqual({
      sceneId: 'scene-1',
      sceneName: 'Named scene',
    });

    expect(
      resolveSelectedSceneTransition(
        { id: 'scene-2' },
        (sceneId) => (sceneId === 'scene-2' ? 'Resolved scene' : null)
      )
    ).toEqual({
      sceneId: 'scene-2',
      sceneName: 'Resolved scene',
    });

    expect(
      resolveSelectedSceneTransition(
        { id: ' scene-3 ', name: ' undefined ' },
        () => ' Resolved scene '
      )
    ).toEqual({
      sceneId: 'scene-3',
      sceneName: 'Resolved scene',
    });
  });
});
