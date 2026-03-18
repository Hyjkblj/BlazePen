import axios from 'axios';
import type { AxiosRequestConfig } from 'axios';
import type { ApiErrorData } from '@/types/api';
import { logger } from '@/utils/logger';

const httpClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

export const unwrapApiData = <T>(response: unknown): T => {
  if (isRecord(response) && 'data' in response) {
    return response.data as T;
  }
  return response as T;
};

export const getErrorStatus = (error: unknown): number | undefined =>
  axios.isAxiosError(error) ? error.response?.status : undefined;

export const getErrorData = (error: unknown): ApiErrorData | undefined => {
  if (!axios.isAxiosError(error)) return undefined;
  const data = error.response?.data;
  return isRecord(data) ? (data as ApiErrorData) : undefined;
};

export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) return getErrorData(error)?.message ?? error.message;
  if (error instanceof Error) return error.message;
  return String(error);
};

export const isTimeoutError = (error: unknown): boolean => {
  if (axios.isAxiosError(error)) {
    return error.code === 'ECONNABORTED' || Boolean(error.message?.includes('timeout'));
  }
  if (error instanceof Error) return error.message.includes('timeout');
  return false;
};

httpClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

httpClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      if (status === 401) {
        localStorage.removeItem('token');
        logger.warn('Unauthorized request, token removed.');
      } else if (status === 403) {
        logger.error('Forbidden request.');
      } else if (status === 404) {
        logger.error('Resource not found.');
      } else if (status === 500) {
        logger.error('Server error.');
      } else {
        logger.error('Request failed:', getErrorMessage(error));
      }
    } else {
      logger.error('Network error:', getErrorMessage(error));
    }
    return Promise.reject(error);
  }
);

export const request = <T>(config: AxiosRequestConfig): Promise<T> =>
  httpClient.request(config).then((response) => unwrapApiData<T>(response));

export default httpClient;
