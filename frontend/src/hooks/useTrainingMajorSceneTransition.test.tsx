// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { TrainingScenario } from '@/types/training';
import { useTrainingMajorSceneTransition } from './useTrainingMajorSceneTransition';

const createScenario = (overrides: Partial<TrainingScenario> = {}): TrainingScenario => ({
  id: 'S1',
  title: 'Major Scene One',
  eraDate: '',
  location: '',
  brief: '',
  mission: '',
  decisionFocus: '',
  targetSkills: [],
  riskTags: [],
  options: [],
  completionHint: '',
  recommendation: null,
  ...overrides,
});

describe('useTrainingMajorSceneTransition', () => {
  it('falls back to scenario id when major-scene metadata is missing', () => {
    const scenario = createScenario({
      id: 'scenario-fallback-1',
      title: 'Fallback Scene',
      sceneLevel: null,
      majorSceneId: null,
      majorSceneOrder: null,
    });

    const { result, rerender } = renderHook(
      ({ sessionId, currentScenario, sessionCompleted }) =>
        useTrainingMajorSceneTransition(sessionId, currentScenario, sessionCompleted),
      {
        initialProps: {
          sessionId: 'session-1',
          currentScenario: scenario as TrainingScenario | null,
          sessionCompleted: false,
        },
      }
    );

    expect(result.current.showMajorTransition).toBe(true);
    expect(result.current.majorTransitionTitle).toBe('Fallback Scene');
    expect(result.current.majorTransitionAct).toBe(1);

    act(() => {
      result.current.dismissMajorTransition();
    });
    expect(result.current.showMajorTransition).toBe(false);

    rerender({
      sessionId: 'session-1',
      currentScenario: scenario,
      sessionCompleted: false,
    });
    expect(result.current.showMajorTransition).toBe(false);
  });

  it('does not replay transition across micro scenes under the same major scene id', () => {
    const firstMicro = createScenario({
      id: 'S1-micro-1',
      title: 'S1 Route A',
      sceneLevel: 'micro',
      majorSceneId: 'S1',
      majorSceneOrder: 2,
    });
    const secondMicro = createScenario({
      id: 'S1-micro-2',
      title: 'S1 Route B',
      sceneLevel: 'micro',
      majorSceneId: 'S1',
      majorSceneOrder: 2,
    });

    const { result, rerender } = renderHook(
      ({ sessionId, currentScenario, sessionCompleted }) =>
        useTrainingMajorSceneTransition(sessionId, currentScenario, sessionCompleted),
      {
        initialProps: {
          sessionId: 'session-1',
          currentScenario: firstMicro as TrainingScenario | null,
          sessionCompleted: false,
        },
      }
    );

    expect(result.current.showMajorTransition).toBe(true);
    act(() => {
      result.current.dismissMajorTransition();
    });
    expect(result.current.showMajorTransition).toBe(false);

    rerender({
      sessionId: 'session-1',
      currentScenario: secondMicro,
      sessionCompleted: false,
    });
    expect(result.current.showMajorTransition).toBe(false);
  });
});
