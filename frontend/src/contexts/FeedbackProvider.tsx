import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { CloseIcon } from '@/components/icons';
import './feedback.css';
import type {
  FeedbackContextValue,
  FeedbackOptions,
  FeedbackToast,
  FeedbackTone,
} from './feedbackCore';
import { FeedbackContext } from './feedbackCore';

const DEFAULT_DURATION: Record<FeedbackTone, number> = {
  success: 2600,
  info: 2600,
  warning: 3200,
  error: 4200,
};

const MAX_TOASTS = 4;

const FEEDBACK_LABELS: Record<FeedbackTone, string> = {
  success: '成功',
  info: '提示',
  warning: '警告',
  error: '错误',
};

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<FeedbackToast[]>([]);
  const nextIdRef = useRef(0);
  const timerMapRef = useRef<Map<number, number>>(new Map());

  const clearTimer = useCallback((id: number) => {
    const timerId = timerMapRef.current.get(id);
    if (timerId === undefined) {
      return;
    }

    window.clearTimeout(timerId);
    timerMapRef.current.delete(id);
  }, []);

  const dismiss = useCallback(
    (id: number) => {
      clearTimer(id);

      startTransition(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
      });
    },
    [clearTimer]
  );

  const pushToast = useCallback(
    (tone: FeedbackTone, message: string, options?: FeedbackOptions) => {
      const trimmedMessage = message.trim();
      if (!trimmedMessage) {
        return;
      }

      const id = nextIdRef.current + 1;
      nextIdRef.current = id;

      startTransition(() => {
        setToasts((current) => {
          const overflowCount = Math.max(0, current.length - (MAX_TOASTS - 1));
          if (overflowCount > 0) {
            current.slice(0, overflowCount).forEach((toast) => clearTimer(toast.id));
          }

          return [
            ...current.slice(overflowCount),
            { id, tone, message: trimmedMessage },
          ];
        });
      });

      const duration = options?.duration ?? DEFAULT_DURATION[tone];
      if (duration > 0) {
        const timerId = window.setTimeout(() => {
          dismiss(id);
        }, duration);
        timerMapRef.current.set(id, timerId);
      }
    },
    [clearTimer, dismiss]
  );

  useEffect(() => {
    const timerMap = timerMapRef.current;

    return () => {
      for (const timerId of timerMap.values()) {
        window.clearTimeout(timerId);
      }
      timerMap.clear();
    };
  }, []);

  const value = useMemo<FeedbackContextValue>(
    () => ({
      success: (message, options) => pushToast('success', message, options),
      info: (message, options) => pushToast('info', message, options),
      warning: (message, options) => pushToast('warning', message, options),
      error: (message, options) => pushToast('error', message, options),
      dismiss,
    }),
    [dismiss, pushToast]
  );

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      <div className="feedback-stack" aria-live="polite" aria-relevant="additions text">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`feedback-toast feedback-toast-${toast.tone}`}
            role={toast.tone === 'error' || toast.tone === 'warning' ? 'alert' : 'status'}
          >
            <div className="feedback-toast-body">
              <div className="feedback-toast-label">{FEEDBACK_LABELS[toast.tone]}</div>
              <div className="feedback-toast-message">{toast.message}</div>
            </div>
            <button
              type="button"
              className="feedback-toast-close"
              onClick={() => dismiss(toast.id)}
              aria-label="关闭提示"
            >
              <CloseIcon />
            </button>
          </div>
        ))}
      </div>
    </FeedbackContext.Provider>
  );
}
