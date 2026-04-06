import { useCallback, useEffect, useRef, useState } from 'react';
import type { TrainingScenario } from '@/types/training';

function deriveMajorScenePresentation(scenario: TrainingScenario): {
  key: string;
  displayTitle: string;
  actNumber: number;
} | null {
  const majorId = scenario.majorSceneId?.trim();
  const level = (scenario.sceneLevel ?? '').toLowerCase();
  if (majorId) {
    const order = scenario.majorSceneOrder;
    const actNumber = typeof order === 'number' && order > 0 ? order : 1;
    let displayTitle = scenario.title?.trim() || majorId;
    if (level === 'micro' && displayTitle.includes('·')) {
      const head = displayTitle.split('·')[0]?.trim();
      if (head) {
        displayTitle = head;
      }
    }
    return { key: majorId, displayTitle, actNumber };
  }
  if (level === 'major') {
    return {
      key: scenario.id,
      displayTitle: scenario.title?.trim() || scenario.id,
      actNumber: 1,
    };
  }

  // Compatibility fallback: if backend has not provided storyline major-scene fields yet,
  // still show transition on scenario switches so the UX does not silently degrade.
  const fallbackScenarioId = scenario.id?.trim();
  if (fallbackScenarioId) {
    const order = scenario.majorSceneOrder;
    const actNumber = typeof order === 'number' && order > 0 ? order : 1;
    return {
      key: `scenario:${fallbackScenarioId}`,
      displayTitle: scenario.title?.trim() || fallbackScenarioId,
      actNumber,
    };
  }

  return null;
}

/**
 * 在训练主线中，当 major_scene_id 变化（进入新的大场景）时触发与故事模式类似的过场层。
 * 同一大场景下的多个小场景不重复播放。
 */
export function useTrainingMajorSceneTransition(
  sessionId: string | null | undefined,
  currentScenario: TrainingScenario | null,
  sessionCompleted: boolean
): {
  showMajorTransition: boolean;
  majorTransitionTitle: string;
  majorTransitionAct: number;
  dismissMajorTransition: () => void;
} {
  const [open, setOpen] = useState(false);
  const [sceneName, setSceneName] = useState('');
  const [actNumber, setActNumber] = useState(1);
  const pendingKeyRef = useRef<string | null>(null);
  const dismissedMajorKeyRef = useRef<string | null>(null);
  const prevSessionRef = useRef<string | null>(null);

  useEffect(() => {
    const sid = sessionId ?? null;
    if (sid !== prevSessionRef.current) {
      prevSessionRef.current = sid;
      dismissedMajorKeyRef.current = null;
      pendingKeyRef.current = null;
      setOpen(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionCompleted || !currentScenario) {
      return;
    }
    const derived = deriveMajorScenePresentation(currentScenario);
    if (!derived) {
      return;
    }
    if (derived.key === dismissedMajorKeyRef.current) {
      return;
    }
    if (open) {
      return;
    }
    pendingKeyRef.current = derived.key;
    setSceneName(derived.displayTitle);
    setActNumber(derived.actNumber);
    setOpen(true);
  }, [currentScenario, sessionCompleted, open]);

  const dismissMajorTransition = useCallback(() => {
    if (pendingKeyRef.current !== null) {
      dismissedMajorKeyRef.current = pendingKeyRef.current;
      pendingKeyRef.current = null;
    }
    setOpen(false);
  }, []);

  return {
    showMajorTransition: open,
    majorTransitionTitle: sceneName,
    majorTransitionAct: actNumber,
    dismissMajorTransition,
  };
}
