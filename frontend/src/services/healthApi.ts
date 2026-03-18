import axios from 'axios';
import { logger } from '@/utils/logger';

export const checkServerHealth = async (): Promise<boolean> => {
  try {
    const response = await axios.get('/health', { timeout: 5000 });
    return response.status === 200;
  } catch (error: unknown) {
    logger.error('Backend health check failed:', error);
    return false;
  }
};
