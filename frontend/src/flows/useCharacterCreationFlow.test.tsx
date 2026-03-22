// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackProvider, GameFlowProvider } from '@/contexts';
import { createCharacter } from '@/services/characterApi';
import { checkServerHealth } from '@/services/healthApi';
import { useCharacterCreationFlow } from './useCharacterCreationFlow';

const telemetrySpy = vi.hoisted(() => vi.fn());

vi.mock('@/services/characterApi', () => ({
  createCharacter: vi.fn(),
}));

vi.mock('@/services/healthApi', () => ({
  checkServerHealth: vi.fn(),
}));

vi.mock('@/services/frontendTelemetry', () => ({
  trackFrontendTelemetry: telemetrySpy,
}));

const wrapper = ({ children }: { children: ReactNode }) => (
  <MemoryRouter>
    <FeedbackProvider>
      <GameFlowProvider>{children}</GameFlowProvider>
    </FeedbackProvider>
  </MemoryRouter>
);

describe('useCharacterCreationFlow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('emits telemetry for a successful character creation submission', async () => {
    vi.mocked(checkServerHealth).mockResolvedValueOnce(true);
    vi.mocked(createCharacter).mockResolvedValueOnce({
      characterId: 'character-77',
      name: 'Test Character',
      imageUrl: '/character.png',
      imageUrls: ['/character.png'],
    });

    const { result } = renderHook(() => useCharacterCreationFlow(), { wrapper });

    await act(async () => {
      const submitPromise = result.current.submit();
      await vi.advanceTimersByTimeAsync(500);
      await submitPromise;
    });

    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'character',
        event: 'character.create',
        status: 'requested',
      })
    );
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'character',
        event: 'character.create',
        status: 'succeeded',
        metadata: expect.objectContaining({
          characterId: 'character-77',
        }),
      })
    );
  });
});

