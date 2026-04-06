import { useEffect, useRef, useState } from 'react';

/**
 * 场景切换淡入淡出 hook。
 * 当 sceneKey 变化时，先触发淡出，再触发淡入。
 * 用于小场景之间的无缝衔接，不需要全屏过场动画。
 */
export function useSceneFadeTransition(sceneKey: string | null | undefined): {
  /** 当前是否处于淡出阶段（内容应隐藏或半透明） */
  isFadingOut: boolean;
  /** 当前是否处于淡入阶段（内容正在显现） */
  isFadingIn: boolean;
} {
  const [phase, setPhase] = useState<'idle' | 'fade-out' | 'fade-in'>('idle');
  const prevKeyRef = useRef<string | null | undefined>(sceneKey);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (sceneKey === prevKeyRef.current) {
      return;
    }

    // 首次挂载（prevKey 为 undefined）直接淡入，不淡出
    const isFirstMount = prevKeyRef.current === undefined;
    prevKeyRef.current = sceneKey;

    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
    }

    if (isFirstMount) {
      setPhase('fade-in');
      timerRef.current = setTimeout(() => setPhase('idle'), 600);
      return;
    }

    // 场景切换：先淡出 300ms，再淡入 500ms
    setPhase('fade-out');
    timerRef.current = setTimeout(() => {
      setPhase('fade-in');
      timerRef.current = setTimeout(() => setPhase('idle'), 500);
    }, 300);

    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, [sceneKey]);

  return {
    isFadingOut: phase === 'fade-out',
    isFadingIn: phase === 'fade-in',
  };
}
