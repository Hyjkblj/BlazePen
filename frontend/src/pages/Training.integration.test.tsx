// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ROUTES } from '@/config/routes';
import type { TrainingFlowState } from '@/contexts/trainingFlowCore';
import type { TrainingRuntimeState } from '@/types/training';

let initialTrainingFlowState: TrainingFlowState = {
  activeSession: null,
};

vi.mock('@/contexts/trainingFlowCore', async () => {
  const actual = await vi.importActual<typeof import('@/contexts/trainingFlowCore')>(
    '@/contexts/trainingFlowCore'
  );

  return {
    ...actual,
    createTrainingFlowState: vi.fn(() => initialTrainingFlowState),
  };
});

const createRuntimeState = (): TrainingRuntimeState => ({
  currentRoundNo: 2,
  currentSceneId: 'scenario-2',
  kState: {
    K1: 0.45,
  },
  sState: {
    source_safety: 0.88,
  },
  runtimeFlags: {
    panicTriggered: false,
    sourceExposed: false,
    editorLocked: false,
    highRiskPath: false,
  },
  stateBar: {
    editorTrust: 0.7,
    publicStability: 0.8,
    sourceSafety: 0.88,
  },
  playerProfile: null,
});

const renderAppAt = async (pathname: string) => {
  vi.resetModules();
  window.history.replaceState({}, '', pathname);
  const { default: App } = await import('@/App');
  return render(<App />);
};

describe('Training route integration', () => {
  beforeEach(() => {
    initialTrainingFlowState = {
      activeSession: null,
    };
    window.history.replaceState({}, '', ROUTES.HOME);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('mounts the training shell through App routing and clears the active training session', async () => {
    initialTrainingFlowState = {
      activeSession: {
        sessionId: 'training-session-1',
        trainingMode: 'adaptive',
        characterId: 'character-7',
        status: 'active',
        roundNo: 2,
        totalRounds: 6,
        runtimeState: createRuntimeState(),
      },
    };

    await renderAppAt(ROUTES.TRAINING);

    expect(await screen.findByText('Training Frontend Shell')).toBeTruthy();
    expect(screen.getByText('training-session-1')).toBeTruthy();
    expect(screen.getByText('scenario-2')).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: '清空活动训练会话' }));

    await waitFor(() => {
      expect(screen.queryByText('training-session-1')).toBeNull();
      expect(screen.queryByRole('button', { name: '清空活动训练会话' })).toBeNull();
    });
  });

  it('keeps the story entry route stable when the global training provider is present', async () => {
    await renderAppAt(ROUTES.HOME);

    expect(await screen.findByRole('button', { name: 'BEGIN' })).toBeTruthy();
    expect(screen.queryByText('Training Frontend Shell')).toBeNull();
  });
});
