import { beforeEach, describe, expect, it, vi } from 'vitest';
import httpClient, { getErrorData, getErrorStatus } from '@/services/httpClient';
import { getStorySessionSnapshot, processGameInput } from './gameApi';

vi.mock('@/services/httpClient', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  getErrorData: vi.fn(),
  getErrorStatus: vi.fn(),
  unwrapApiData: vi.fn((value: unknown) => value),
}));

describe('gameApi story session error mapping', () => {
  beforeEach(() => {
    vi.mocked(httpClient.post).mockReset();
    vi.mocked(httpClient.get).mockReset();
    vi.mocked(getErrorData).mockReset();
    vi.mocked(getErrorStatus).mockReset();
  });

  it.each([
    ['STORY_SESSION_NOT_FOUND', 404],
    ['STORY_SESSION_EXPIRED', 410],
    ['STORY_SESSION_RESTORE_FAILED', 400],
  ] as const)(
    'preserves backend story session error code %s during turn submission',
    async (backendErrorCode, status) => {
      const requestError = new Error(`backend returned ${backendErrorCode}`);
      vi.mocked(httpClient.post).mockRejectedValueOnce(requestError);
      vi.mocked(getErrorStatus).mockReturnValueOnce(status);
      vi.mocked(getErrorData).mockReturnValueOnce({
        message: `${backendErrorCode} message`,
        error: {
          code: backendErrorCode,
        },
      });

      await expect(
        processGameInput({
          threadId: 'thread-1',
          userInput: 'option:1',
          characterId: 'character-1',
        })
      ).rejects.toMatchObject({
          code: backendErrorCode,
          message: `${backendErrorCode} message`,
          status,
        });
    }
  );

  it('preserves backend story session restore failure during snapshot restore', async () => {
    const requestError = new Error('snapshot restore failed');
    vi.mocked(httpClient.get).mockRejectedValueOnce(requestError);
    vi.mocked(getErrorStatus).mockReturnValueOnce(400);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'Snapshot restore failed.',
      error: {
        code: 'STORY_SESSION_RESTORE_FAILED',
      },
    });

    await expect(getStorySessionSnapshot('thread-1')).rejects.toMatchObject({
        code: 'STORY_SESSION_RESTORE_FAILED',
        message: 'Snapshot restore failed.',
        status: 400,
      });
  });
});
