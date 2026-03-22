import { getServiceErrorMessage, isServiceError } from '@/services/serviceError';

export const isStorySessionLocalFallbackCandidate = (error: unknown): boolean =>
  isServiceError(error) &&
  (error.code === 'REQUEST_TIMEOUT' || error.code === 'SERVICE_UNAVAILABLE');

export const getStorySessionLocalFallbackWarning = (error: unknown): string | null => {
  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return 'Server restore timed out. Loaded the last local story snapshot in read-only mode.';
  }

  if (isServiceError(error) && error.code === 'SERVICE_UNAVAILABLE') {
    return 'Story restore service is unavailable. Loaded the last local story snapshot in read-only mode.';
  }

  return null;
};

export const getStorySessionRestoreFailureMessage = (
  error: unknown,
  fallbackMessage: string
): string => {
  if (isServiceError(error) && error.code === 'STORY_SESSION_NOT_FOUND') {
    return 'Story session could not be found. Please restart the story.';
  }

  if (
    isServiceError(error) &&
    (error.code === 'STORY_SESSION_EXPIRED' || error.code === 'SESSION_EXPIRED')
  ) {
    return 'Story session expired. Please restart the story.';
  }

  if (isServiceError(error) && error.code === 'STORY_SESSION_RESTORE_FAILED') {
    return 'Story session recovery failed. Please restart the story.';
  }

  if (isServiceError(error) && error.code === 'REQUEST_TIMEOUT') {
    return 'Story session restore timed out. Please retry.';
  }

  return getServiceErrorMessage(error, fallbackMessage);
};
