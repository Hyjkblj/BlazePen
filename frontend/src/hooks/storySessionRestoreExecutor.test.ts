import { describe, expect, it } from 'vitest';
import { ServiceError } from '@/services/serviceError';
import {
  getStorySessionLocalFallbackWarning,
  getStorySessionRestoreFailureMessage,
  isStorySessionLocalFallbackCandidate,
} from './storySessionRestoreExecutor';

describe('storySessionRestoreExecutor', () => {
  it('marks timeout and service unavailable as local fallback candidates', () => {
    expect(
      isStorySessionLocalFallbackCandidate(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).toBe(true);

    expect(
      isStorySessionLocalFallbackCandidate(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'service unavailable',
        })
      )
    ).toBe(true);

    expect(
      isStorySessionLocalFallbackCandidate(
        new ServiceError({
          code: 'STORY_SESSION_EXPIRED',
          message: 'expired',
        })
      )
    ).toBe(false);
  });

  it('returns structured local fallback warnings for transient restore failures', () => {
    expect(
      getStorySessionLocalFallbackWarning(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        })
      )
    ).toBe('Server restore timed out. Loaded the last local story snapshot in read-only mode.');

    expect(
      getStorySessionLocalFallbackWarning(
        new ServiceError({
          code: 'SERVICE_UNAVAILABLE',
          message: 'service unavailable',
        })
      )
    ).toBe(
      'Story restore service is unavailable. Loaded the last local story snapshot in read-only mode.'
    );

    expect(
      getStorySessionLocalFallbackWarning(
        new ServiceError({
          code: 'STORY_SESSION_NOT_FOUND',
          message: 'not found',
        })
      )
    ).toBeNull();
  });

  it('maps restore failures to stable user-facing messages', () => {
    expect(
      getStorySessionRestoreFailureMessage(
        new ServiceError({
          code: 'STORY_SESSION_NOT_FOUND',
          message: 'not found',
        }),
        'fallback'
      )
    ).toBe('Story session could not be found. Please restart the story.');

    expect(
      getStorySessionRestoreFailureMessage(
        new ServiceError({
          code: 'SESSION_EXPIRED',
          message: 'expired',
        }),
        'fallback'
      )
    ).toBe('Story session expired. Please restart the story.');

    expect(
      getStorySessionRestoreFailureMessage(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          message: 'timeout',
        }),
        'fallback'
      )
    ).toBe('Story session restore timed out. Please retry.');
  });

  it('falls back to service error message for unknown restore failures', () => {
    expect(
      getStorySessionRestoreFailureMessage(new Error('backend unstable'), 'fallback')
    ).toBe('backend unstable');
  });
});
