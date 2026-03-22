import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { InitialGameData } from '@/types/game';
import { executeGameInitializationPlan } from './gameInitializationExecutor';

vi.mock('@/services/frontendTelemetry', () => ({
  trackFrontendTelemetry: vi.fn(),
}));

vi.mock('@/services/gameApi', () => ({
  initGame: vi.fn(),
  initializeStory: vi.fn(),
}));

vi.mock('@/storage/storySessionCache', () => ({
  readStoryThreadSave: vi.fn(),
}));

import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { initGame, initializeStory } from '@/services/gameApi';
import { readStoryThreadSave } from '@/storage/storySessionCache';

const createActions = () => ({
  replaceMessages: vi.fn(),
  startLoading: vi.fn(),
  stopLoading: vi.fn(),
  setThreadId: vi.fn(),
  setCharacterId: vi.fn(),
  setCharacterImageUrl: vi.fn(),
  setDialogue: vi.fn(),
  setOptions: vi.fn(),
  setGameFinished: vi.fn(),
  enterScene: vi.fn(),
  applyCompositeScene: vi.fn(),
  applySceneVisual: vi.fn(),
});

const createExecutorOptions = () => ({
  actions: createActions(),
  feedback: {
    error: vi.fn(),
  },
  characterDraft: null,
  clearRestoreSession: vi.fn(),
  clearInitialGameData: vi.fn(),
  clearActiveSession: vi.fn(),
  setActiveSession: vi.fn(),
  setCurrentCharacterId: vi.fn(),
  applyStoryData: vi.fn(),
  applyInitialEntryData: vi.fn(),
  restoreFromServerSnapshot: vi.fn(),
  notifyLocalRestoreFallback: vi.fn(),
  notifyRestoreFailure: vi.fn(),
});

describe('executeGameInitializationPlan', () => {
  beforeEach(() => {
    vi.mocked(trackFrontendTelemetry).mockReset();
    vi.mocked(initGame).mockReset();
    vi.mocked(initializeStory).mockReset();
    vi.mocked(readStoryThreadSave).mockReset();
  });

  it('hydrates and reactivates the restored story session on restore-session success', async () => {
    const options = createExecutorOptions();
    options.restoreFromServerSnapshot.mockResolvedValue({
      restored: true,
      source: 'server',
    });

    await executeGameInitializationPlan({
      ...options,
      plan: {
        kind: 'restore-session',
        threadId: 'thread-restore',
        characterId: 'character-1',
        selectedSceneTransition: null,
      },
    });

    expect(options.restoreFromServerSnapshot).toHaveBeenCalledWith(
      'thread-restore',
      'character-1'
    );
    expect(options.clearRestoreSession).toHaveBeenCalledTimes(1);
    expect(options.actions.setThreadId).toHaveBeenCalledWith('thread-restore');
    expect(options.actions.setCharacterId).toHaveBeenCalledWith('character-1');
    expect(options.setCurrentCharacterId).toHaveBeenCalledWith('character-1');
    expect(options.setActiveSession).toHaveBeenCalledWith({
      threadId: 'thread-restore',
      characterId: 'character-1',
      initialGameData: null,
    });
    expect(options.notifyRestoreFailure).not.toHaveBeenCalled();
  });

  it('reuses persisted initial story data during resume-session when there is no local save', async () => {
    const options = createExecutorOptions();
    const initialGameData: InitialGameData = {
      sceneId: 'study_room',
      storyBackground: 'Opening background',
      characterDialogue: 'Opening dialogue',
      playerOptions: [],
      compositeImageUrl: null,
      sceneImageUrl: null,
      isGameFinished: false,
    };

    vi.mocked(readStoryThreadSave).mockReturnValueOnce(null);

    await executeGameInitializationPlan({
      ...options,
      plan: {
        kind: 'resume-session',
        threadId: 'thread-active',
        characterId: 'character-2',
        initialGameData,
        selectedSceneTransition: {
          sceneId: 'study_room',
          sceneName: 'Study Room',
        },
      },
    });

    expect(options.restoreFromServerSnapshot).not.toHaveBeenCalled();
    expect(options.actions.setThreadId).toHaveBeenCalledWith('thread-active');
    expect(options.actions.setCharacterId).toHaveBeenCalledWith('character-2');
    expect(options.setCurrentCharacterId).toHaveBeenCalledWith('character-2');
    expect(options.applyInitialEntryData).toHaveBeenCalledWith(initialGameData, {
      characterId: 'character-2',
      selectedSceneTransition: {
        sceneId: 'study_room',
        sceneName: 'Study Room',
      },
    });
    expect(options.clearInitialGameData).toHaveBeenCalledTimes(1);
  });

  it('falls back to local read-only mode during resume-session when server restore can only use local data', async () => {
    const options = createExecutorOptions();
    const restoreError = new Error('restore timed out');

    vi.mocked(readStoryThreadSave).mockReturnValueOnce({
      threadId: 'thread-active',
      messages: [],
      timestamp: 1,
    });
    options.restoreFromServerSnapshot.mockResolvedValue({
      restored: true,
      source: 'local',
      error: restoreError,
    });

    await executeGameInitializationPlan({
      ...options,
      plan: {
        kind: 'resume-session',
        threadId: 'thread-active',
        characterId: 'character-2',
        initialGameData: null,
        selectedSceneTransition: null,
      },
    });

    expect(options.restoreFromServerSnapshot).toHaveBeenCalledWith(
      'thread-active',
      'character-2'
    );
    expect(options.clearInitialGameData).toHaveBeenCalledTimes(1);
    expect(options.clearActiveSession).toHaveBeenCalledTimes(1);
    expect(options.actions.setThreadId).toHaveBeenCalledWith(null);
    expect(options.actions.setCharacterId).toHaveBeenCalledWith('character-2');
    expect(options.setCurrentCharacterId).toHaveBeenCalledWith('character-2');
    expect(options.notifyLocalRestoreFallback).toHaveBeenCalledWith(restoreError);
    expect(options.notifyRestoreFailure).not.toHaveBeenCalled();
  });

  it('initializes a fresh story session through the story init pipeline', async () => {
    const options = createExecutorOptions();
    const storyData = {
      sceneId: 'cafe_nearby',
      storyBackground: 'A quiet cafe',
      characterDialogue: 'Welcome back.',
      playerOptions: [{ id: 1, text: 'Sit down', type: 'action' }],
      compositeImageUrl: null,
      sceneImageUrl: '/scene.png',
      isGameFinished: false,
    };

    vi.mocked(initGame).mockResolvedValueOnce({
      threadId: 'thread-new',
      userId: null,
      gameMode: 'solo',
    });
    vi.mocked(initializeStory).mockResolvedValueOnce(storyData);

    await executeGameInitializationPlan({
      ...options,
      characterDraft: {
        characterId: 'character-3',
        imageUrl: '/draft-character.png',
      },
      plan: {
        kind: 'fresh-session',
        characterId: 'character-3',
        selectedSceneTransition: {
          sceneId: 'cafe_nearby',
          sceneName: 'Cafe Nearby',
        },
      },
    });

    expect(vi.mocked(trackFrontendTelemetry)).toHaveBeenNthCalledWith(1, {
      domain: 'story',
      event: 'story.init',
      status: 'requested',
      metadata: {
        initializationKind: 'fresh-session',
        characterId: 'character-3',
        sceneId: 'cafe_nearby',
      },
    });
    expect(vi.mocked(initGame)).toHaveBeenCalledWith({
      gameMode: 'solo',
      characterId: 'character-3',
    });
    expect(vi.mocked(initializeStory)).toHaveBeenCalledWith(
      'thread-new',
      'character-3',
      'cafe_nearby',
      '/draft-character.png'
    );
    expect(options.actions.setThreadId).toHaveBeenCalledWith('thread-new');
    expect(options.actions.setCharacterId).toHaveBeenCalledWith('character-3');
    expect(options.setCurrentCharacterId).toHaveBeenCalledWith('character-3');
    expect(options.setActiveSession).toHaveBeenCalledWith({
      threadId: 'thread-new',
      characterId: 'character-3',
      initialGameData: null,
    });
    expect(options.applyStoryData).toHaveBeenCalledWith(storyData, {
      characterId: 'character-3',
      sceneMode: 'reset',
    });
    expect(options.actions.replaceMessages).toHaveBeenCalledWith([
      { role: 'assistant', content: 'A quiet cafe' },
      { role: 'assistant', content: 'Welcome back.' },
    ]);
    expect(vi.mocked(trackFrontendTelemetry)).toHaveBeenNthCalledWith(2, {
      domain: 'story',
      event: 'story.init',
      status: 'succeeded',
      metadata: {
        initializationKind: 'fresh-session',
        characterId: 'character-3',
        sceneId: 'cafe_nearby',
        threadId: 'thread-new',
        initialSceneId: 'cafe_nearby',
      },
    });
    expect(options.feedback.error).not.toHaveBeenCalled();
  });
});
