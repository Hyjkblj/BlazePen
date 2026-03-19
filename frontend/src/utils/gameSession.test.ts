import { describe, expect, it } from 'vitest';
import {
  buildInitialAssistantMessages,
  hasStorySceneVisual,
  resolveGameInitializationPlan,
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

describe('resolveGameInitializationPlan', () => {
  const resolveSceneName = (sceneId: string) => (sceneId === 'scene-2' ? 'Resolved scene' : null);

  it('prioritizes an explicit restore session over active or fresh initialization inputs', () => {
    expect(
      resolveGameInitializationPlan({
        restoreThreadId: ' restore-thread ',
        restoreCharacterId: 'restore-character',
        activeThreadId: 'active-thread',
        activeCharacterId: 'active-character',
        currentCharacterId: 'current-character',
        draftCharacterId: 'draft-character',
        selectedScene: { id: 'scene-2' },
        resolveSceneName,
      })
    ).toEqual({
      kind: 'restore-session',
      threadId: 'restore-thread',
      characterId: 'restore-character',
      selectedSceneTransition: {
        sceneId: 'scene-2',
        sceneName: 'Resolved scene',
      },
    });
  });

  it('builds a resume-session plan from the persisted active thread even when character ids are partially missing', () => {
    expect(
      resolveGameInitializationPlan({
        activeThreadId: ' active-thread ',
        activeCharacterId: null,
        currentCharacterId: ' current-character ',
        draftCharacterId: 'draft-character',
        initialGameData: {
          sceneId: 'study_room',
          storyBackground: null,
          characterDialogue: 'Recovered intro',
          playerOptions: [],
          compositeImageUrl: null,
          sceneImageUrl: null,
        },
        resolveSceneName,
      })
    ).toEqual({
      kind: 'resume-session',
      threadId: 'active-thread',
      characterId: 'current-character',
      initialGameData: {
        sceneId: 'study_room',
        storyBackground: null,
        characterDialogue: 'Recovered intro',
        playerOptions: [],
        compositeImageUrl: null,
        sceneImageUrl: null,
      },
      selectedSceneTransition: null,
    });
  });

  it('falls back to a fresh session when only a draft character is available', () => {
    expect(
      resolveGameInitializationPlan({
        draftCharacterId: 'draft-character',
        selectedScene: { id: 'scene-2', name: 'Named scene' },
        resolveSceneName,
      })
    ).toEqual({
      kind: 'fresh-session',
      characterId: 'draft-character',
      selectedSceneTransition: {
        sceneId: 'scene-2',
        sceneName: 'Named scene',
      },
    });
  });

  it('returns an idle plan when no recoverable session or character exists', () => {
    expect(
      resolveGameInitializationPlan({
        restoreThreadId: ' undefined ',
        activeThreadId: null,
        currentCharacterId: 'null',
        draftCharacterId: '  ',
        resolveSceneName,
      })
    ).toEqual({
      kind: 'idle',
      selectedSceneTransition: null,
    });
  });
});
