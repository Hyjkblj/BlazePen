import { describe, expect, it } from 'vitest';
import {
  normalizeStoryEndingCheckPayload,
  normalizeStoryEndingSummaryPayload,
  normalizeInitialGameData,
  normalizeStoryScenePayload,
  normalizeStorySessionHistoryPayload,
  normalizeStorySessionSnapshotPayload,
  normalizeStoryTurnPayload,
  resolveSceneImageAsset,
  resolveStorySceneVisual,
  toStoryEndingCheckResult,
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
      isGameFinished: true,
    });
  });
});

describe('normalizeStoryTurnPayload', () => {
  it('normalizes session recovery metadata together with story scene fields', () => {
    expect(
      normalizeStoryTurnPayload({
        thread_id: ' thread-next ',
        session_restored: true,
        need_reselect_option: true,
        restored_from_thread_id: ' thread-old ',
        scene: 'study_room',
        character_dialogue: 'Please choose again.',
        player_options: [{ id: 1, text: 'Retry', type: 'action' }],
      })
    ).toEqual({
      threadId: 'thread-next',
      sessionRestored: true,
      needReselectOption: true,
      restoredFromThreadId: 'thread-old',
      sceneId: 'study_room',
      sceneImageUrl: null,
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Please choose again.',
      playerOptions: [{ id: 1, text: 'Retry', type: 'action' }],
      isGameFinished: false,
    });
  });
});

describe('normalizeStorySessionSnapshotPayload', () => {
  it('restores story state from nested snapshot fields when the top-level payload is summary-only', () => {
    expect(
      normalizeStorySessionSnapshotPayload({
        thread_id: 'thread-live',
        status: 'in_progress',
        round_no: 3,
        snapshot: {
          scene: 'study_room',
          story_background: 'Recovered background',
          character_dialogue: 'Recovered dialogue',
          player_options: [{ id: 2, text: 'Keep going', type: 'action' }],
          composite_image_url: '/restored-composite.png',
          updated_at: '2026-03-19T12:00:00Z',
          expires_at: '2026-03-19T12:30:00Z',
        },
      })
    ).toEqual({
      threadId: 'thread-live',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'study_room',
      sceneImageUrl: null,
      compositeImageUrl: '/restored-composite.png',
      storyBackground: 'Recovered background',
      characterDialogue: 'Recovered dialogue',
      playerOptions: [{ id: 2, text: 'Keep going', type: 'action' }],
      isGameFinished: false,
      roundNo: 3,
      status: 'in_progress',
      updatedAt: '2026-03-19T12:00:00Z',
      expiresAt: '2026-03-19T12:30:00Z',
    });
  });
});

describe('normalizeStorySessionHistoryPayload', () => {
  it('normalizes canonical story history into a stable frontend read model', () => {
    expect(
      normalizeStorySessionHistoryPayload({
        thread_id: ' thread-live ',
        status: ' completed ',
        current_round_no: 4,
        latest_scene: ' study_room ',
        updated_at: '2026-03-20T12:00:00Z',
        expires_at: '2026-03-20T12:30:00Z',
        history: [
          {
            round_no: 1,
            status: 'in_progress',
            scene: 'study_room',
            event_title: 'First Meeting',
            character_dialogue: 'Nice to meet you.',
            user_action: {
              kind: 'option',
              summary: 'Wave back',
              option_index: 0,
              option_text: 'Wave back',
              option_type: 'action',
            },
            state_summary: {
              changes: {
                trust: '10',
                favorability: 4,
              },
              current_states: {
                trust: 60,
                hostility: '12',
              },
            },
            is_event_finished: false,
            is_game_finished: false,
            created_at: '2026-03-20T11:58:00Z',
          },
        ],
      })
    ).toEqual({
      threadId: 'thread-live',
      status: 'completed',
      currentRoundNo: 4,
      latestSceneId: 'study_room',
      updatedAt: '2026-03-20T12:00:00Z',
      expiresAt: '2026-03-20T12:30:00Z',
      history: [
        {
          roundNo: 1,
          status: 'in_progress',
          sceneId: 'study_room',
          eventTitle: 'First Meeting',
          characterDialogue: 'Nice to meet you.',
          userAction: {
            kind: 'option',
            summary: 'Wave back',
            rawInput: null,
            optionIndex: 0,
            optionText: 'Wave back',
            optionType: 'action',
          },
          stateSummary: {
            changes: {
              trust: 10,
              favorability: 4,
            },
            currentStates: {
              trust: 60,
              hostility: 12,
            },
          },
          isEventFinished: false,
          isGameFinished: false,
          createdAt: '2026-03-20T11:58:00Z',
        },
      ],
    });
  });
});

describe('normalizeStoryEndingCheckPayload', () => {
  it('keeps the legacy ending contract stable for compatibility callers', () => {
    expect(
      normalizeStoryEndingCheckPayload({
        has_ending: true,
        ending: {
          type: ' good_ending ',
          description: ' A warm, hopeful ending. ',
          favorability: '68',
          trust: 56,
          hostility: null,
        },
      })
    ).toEqual({
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm, hopeful ending.',
        favorability: 68,
        trust: 56,
        hostility: null,
      },
    });
  });
});

describe('normalizeStoryEndingSummaryPayload', () => {
  it('normalizes the canonical ending summary route into the frontend read model', () => {
    expect(
      normalizeStoryEndingSummaryPayload({
        thread_id: ' thread-ended ',
        status: ' completed ',
        round_no: 6,
        has_ending: true,
        ending: {
          type: ' good_ending ',
          description: ' A warm, hopeful ending. ',
          scene: ' cafe_nearby ',
          event_title: ' Final Promise ',
          key_states: {
            favorability: '68',
            trust: 56,
            hostility: null,
            dependence: '41',
          },
        },
        updated_at: '2026-03-20T10:00:00Z',
        expires_at: '2026-03-20T10:30:00Z',
      })
    ).toEqual({
      threadId: 'thread-ended',
      status: 'completed',
      roundNo: 6,
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm, hopeful ending.',
        sceneId: 'cafe_nearby',
        eventTitle: 'Final Promise',
        keyStates: {
          favorability: 68,
          trust: 56,
          hostility: null,
          dependence: 41,
        },
      },
      updatedAt: '2026-03-20T10:00:00Z',
      expiresAt: '2026-03-20T10:30:00Z',
    });
  });
});

describe('toStoryEndingCheckResult', () => {
  it('adapts the canonical ending summary model into the legacy ending-check shape', () => {
    expect(
      toStoryEndingCheckResult({
        threadId: 'thread-ended',
        status: 'completed',
        roundNo: 6,
        hasEnding: true,
        ending: {
          type: 'good_ending',
          description: 'A warm, hopeful ending.',
          sceneId: 'cafe_nearby',
          eventTitle: 'Final Promise',
          keyStates: {
            favorability: 68,
            trust: 56,
            hostility: null,
            dependence: 41,
          },
        },
        updatedAt: '2026-03-20T10:00:00Z',
        expiresAt: '2026-03-20T10:30:00Z',
      })
    ).toEqual({
      hasEnding: true,
      ending: {
        type: 'good_ending',
        description: 'A warm, hopeful ending.',
        favorability: 68,
        trust: 56,
        hostility: null,
      },
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
        isGameFinished: true,
      })
    ).toEqual({
      sceneId: 'restaurant',
      storyBackground: 'Intro',
      characterDialogue: 'Hi',
      playerOptions: [{ id: 1, text: 'Continue', type: 'action' }],
      compositeImageUrl: null,
      sceneImageUrl: '/scene.png',
      isGameFinished: true,
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
      isGameFinished: false,
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
