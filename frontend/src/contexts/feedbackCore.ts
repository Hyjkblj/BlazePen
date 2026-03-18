import { createContext } from 'react';

export type FeedbackTone = 'success' | 'error' | 'warning' | 'info';

export interface FeedbackOptions {
  duration?: number;
}

export interface FeedbackToast {
  id: number;
  tone: FeedbackTone;
  message: string;
}

export interface FeedbackContextValue {
  success: (message: string, options?: FeedbackOptions) => void;
  error: (message: string, options?: FeedbackOptions) => void;
  warning: (message: string, options?: FeedbackOptions) => void;
  info: (message: string, options?: FeedbackOptions) => void;
  dismiss: (id: number) => void;
}

export const FeedbackContext = createContext<FeedbackContextValue | null>(null);
