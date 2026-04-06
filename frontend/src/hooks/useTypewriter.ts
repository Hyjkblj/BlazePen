import { useCallback, useEffect, useRef, useState } from 'react';

interface UseTypewriterOptions {
  /** 每个字符的间隔毫秒数，默认 30 */
  charIntervalMs?: number;
  /** 文本变化时是否自动重置并重新开始，默认 true */
  autoStart?: boolean;
}

interface UseTypewriterResult {
  /** 当前已显示的文字 */
  displayedText: string;
  /** 打字机是否已完成（全文显示完毕） */
  isDone: boolean;
  /** 立即跳过，显示全文 */
  skip: () => void;
}

/**
 * 打字机效果 hook。
 * - text 变化时自动重置并重新开始
 * - skip() 立即显示全文并标记完成
 */
export function useTypewriter(
  text: string,
  { charIntervalMs = 30, autoStart = true }: UseTypewriterOptions = {}
): UseTypewriterResult {
  const [displayedText, setDisplayedText] = useState('');
  const [isDone, setIsDone] = useState(false);
  const indexRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const textRef = useRef(text);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const skip = useCallback(() => {
    clearTimer();
    setDisplayedText(textRef.current);
    setIsDone(true);
  }, [clearTimer]);

  useEffect(() => {
    textRef.current = text;

    if (!autoStart || !text) {
      clearTimer();
      setDisplayedText(text);
      setIsDone(true);
      return;
    }

    // 重置状态，重新开始打字
    clearTimer();
    indexRef.current = 0;
    setDisplayedText('');
    setIsDone(false);

    const tick = () => {
      indexRef.current += 1;
      const next = textRef.current.slice(0, indexRef.current);
      setDisplayedText(next);

      if (indexRef.current >= textRef.current.length) {
        setIsDone(true);
        return;
      }

      // 标点符号后稍作停顿，增加节奏感
      const lastChar = textRef.current[indexRef.current - 1];
      const isPause = ['。', '！', '？', '…', '\n'].includes(lastChar ?? '');
      timerRef.current = setTimeout(tick, isPause ? charIntervalMs * 6 : charIntervalMs);
    };

    timerRef.current = setTimeout(tick, charIntervalMs);

    return clearTimer;
  }, [text, autoStart, charIntervalMs, clearTimer]);

  return { displayedText, isDone, skip };
}
