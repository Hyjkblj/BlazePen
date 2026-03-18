import { useContext } from 'react';
import { FeedbackContext } from './feedbackCore';

export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (!context) {
    throw new Error('useFeedback must be used within FeedbackProvider.');
  }
  return context;
}
