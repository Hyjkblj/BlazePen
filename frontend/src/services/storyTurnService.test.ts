import { beforeEach, describe, expect, it, vi } from 'vitest';
import { processGameInput } from '@/services/gameApi';
import { ServiceError } from '@/services/serviceError';
import { submitStoryTurn } from './storyTurnService';

vi.mock('@/services/gameApi', () => ({
  processGameInput: vi.fn(),
}));

describe('storyTurnService', () => {
  beforeEach(() => {
    vi.mocked(processGameInput).mockReset();
  });

  it('returns the backend turn payload directly when submission succeeds', async () => {
    vi.mocked(processGameInput).mockResolvedValueOnce({
      threadId: 'thread-live',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Keep going.',
      playerOptions: [{ id: 2, text: 'Continue', type: 'action' }],
      isGameFinished: false,
    });

    await expect(
      submitStoryTurn({
        threadId: 'thread-live',
        userInput: 'option:1',
        characterId: 'character-1',
      })
    ).resolves.toEqual({
      threadId: 'thread-live',
      sessionRestored: false,
      needReselectOption: false,
      restoredFromThreadId: null,
      sceneId: 'study_room',
      sceneImageUrl: '/scene.png',
      compositeImageUrl: null,
      storyBackground: null,
      characterDialogue: 'Keep going.',
      playerOptions: [{ id: 2, text: 'Continue', type: 'action' }],
      isGameFinished: false,
    });
  });

  it('does not create a fresh thread when the backend reports session expiration', async () => {
    const sessionExpiredError = new ServiceError({
      code: 'STORY_SESSION_EXPIRED',
      message: 'Story session expired.',
    });
    vi.mocked(processGameInput).mockRejectedValueOnce(sessionExpiredError);

    await expect(
      submitStoryTurn({
        threadId: 'thread-old',
        userInput: 'option:1',
        characterId: 'character-1',
      })
    ).rejects.toBe(sessionExpiredError);
  });

  it('passes through story session invalidation errors without inventing a restart flow', async () => {
    const sessionMissingError = new ServiceError({
      code: 'STORY_SESSION_NOT_FOUND',
      message: 'Story session missing.',
    });
    vi.mocked(processGameInput).mockRejectedValueOnce(sessionMissingError);

    await expect(
      submitStoryTurn({
        threadId: 'thread-old',
        userInput: 'option:1',
        characterId: 'character-1',
      })
    ).rejects.toBe(sessionMissingError);
  });
});
