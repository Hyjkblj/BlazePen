import httpClient, {
  getErrorData,
  getErrorStatus,
  isTimeoutError,
  unwrapApiData,
} from '@/services/httpClient';
import type {
  GameInitRequest,
  GameInitResponse,
  GameInputRequest,
  GenericApiRecord,
  ProcessGameInputResponse,
} from '@/types/api';
import { logger } from '@/utils/logger';

export const initGame = async (data: GameInitRequest): Promise<GameInitResponse> => {
  try {
    const response = await httpClient.post('/v1/game/init', data, { timeout: 60000 });
    return unwrapApiData<GameInitResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) {
      throw new Error('Game initialization timed out.');
    }
    throw error;
  }
};

export const processGameInput = async (
  data: GameInputRequest
): Promise<ProcessGameInputResponse> => {
  try {
    const response = await httpClient.post('/v1/game/input', data, { timeout: 90000 });
    return unwrapApiData<ProcessGameInputResponse>(response);
  } catch (error: unknown) {
    if (isTimeoutError(error)) {
      throw new Error('Game input processing timed out.');
    }

    const errorData = getErrorData(error);
    if (
      getErrorStatus(error) === 400 &&
      typeof errorData?.message === 'string' &&
      errorData.message.includes('not found')
    ) {
      logger.warn('Game session not found, may require re-init.');
    }

    throw error;
  }
};

export const checkEnding = async (threadId: string): Promise<GenericApiRecord> => {
  const response = await httpClient.get(`/v1/game/check-ending/${threadId}`);
  return unwrapApiData<GenericApiRecord>(response);
};

export const triggerEnding = async (threadId: string): Promise<GenericApiRecord> => {
  const response = await httpClient.post('/v1/game/trigger-ending', { thread_id: threadId });
  return unwrapApiData<GenericApiRecord>(response);
};
