// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import { ServiceError } from '@/services/serviceError';
import { getPresetVoices, setVoiceConfig } from '@/services/ttsApi';
import { useCharacterVoiceSelection } from './useCharacterVoiceSelection';

vi.mock('@/services/ttsApi', () => ({
  getPresetVoices: vi.fn(),
  getVoicePreviewAudio: vi.fn(),
  setVoiceConfig: vi.fn(),
}));

const createFeedbackSpy = (): Pick<FeedbackContextValue, 'warning' | 'error'> => ({
  warning: vi.fn(),
  error: vi.fn(),
});

describe('useCharacterVoiceSelection', () => {
  beforeEach(() => {
    vi.mocked(getPresetVoices).mockReset();
    vi.mocked(setVoiceConfig).mockReset();
  });

  it('loads preset voices when the voice step becomes active', async () => {
    const feedback = createFeedbackSpy();

    vi.mocked(getPresetVoices).mockResolvedValueOnce([
      {
        id: 'voice-1',
        name: '温柔女声',
        gender: 'female',
      },
    ]);

    const { result } = renderHook(() =>
      useCharacterVoiceSelection({
        enabled: true,
        feedback,
        initialSelectedVoiceId: null,
      })
    );

    await waitFor(() => {
      expect(result.current.presetVoices).toHaveLength(1);
    });

    expect(result.current.voicesLoading).toBe(false);
    expect(feedback.warning).not.toHaveBeenCalled();
    expect(feedback.error).not.toHaveBeenCalled();
  });

  it('persists the selected preset voice and returns the local voice config model', async () => {
    const feedback = createFeedbackSpy();

    vi.mocked(getPresetVoices).mockResolvedValueOnce([
      {
        id: 'voice-1',
        name: '冷静男声',
        description: '适合沉稳角色',
        voice_id: 'preset-voice-id',
        gender: 'male',
      },
    ]);
    vi.mocked(setVoiceConfig).mockResolvedValueOnce({});

    const { result } = renderHook(() =>
      useCharacterVoiceSelection({
        enabled: true,
        feedback,
        initialSelectedVoiceId: null,
      })
    );

    await waitFor(() => {
      expect(result.current.presetVoices).toHaveLength(1);
    });

    act(() => {
      result.current.selectVoice('voice-1');
    });

    let persistResult = null;
    await act(async () => {
      persistResult = await result.current.persistSelectedVoiceConfig('101');
    });

    expect(setVoiceConfig).toHaveBeenCalledWith({
      character_id: 101,
      voice_type: 'preset',
      preset_voice_id: 'voice-1',
    });
    expect(persistResult).toEqual({
      status: 'saved',
      voiceConfig: {
        voice_type: 'preset',
        preset_voice_id: 'voice-1',
        voice_name: '冷静男声',
        voice_description: '适合沉稳角色',
        voice_id: 'preset-voice-id',
      },
    });
  });

  it('surfaces voice config persistence failures back to the flow', async () => {
    const feedback = createFeedbackSpy();
    const persistError = new ServiceError({
      code: 'REQUEST_TIMEOUT',
      message: 'Voice config save timed out.',
    });

    vi.mocked(getPresetVoices).mockResolvedValueOnce([
      {
        id: 'voice-1',
        name: '冷静男声',
        gender: 'male',
      },
    ]);
    vi.mocked(setVoiceConfig).mockRejectedValueOnce(persistError);

    const { result } = renderHook(() =>
      useCharacterVoiceSelection({
        enabled: true,
        feedback,
        initialSelectedVoiceId: null,
      })
    );

    await waitFor(() => {
      expect(result.current.presetVoices).toHaveLength(1);
    });

    act(() => {
      result.current.selectVoice('voice-1');
    });

    let persistResult = null;
    await act(async () => {
      persistResult = await result.current.persistSelectedVoiceConfig('101');
    });

    expect(persistResult).toEqual({
      status: 'failed',
      error: persistError,
    });
  });

  it('uses the stable service error model for preset voice load failures', async () => {
    const feedback = createFeedbackSpy();

    vi.mocked(getPresetVoices).mockRejectedValueOnce(
      new ServiceError({
        code: 'SERVICE_UNAVAILABLE',
        message: 'TTS service unavailable.',
      })
    );

    renderHook(() =>
      useCharacterVoiceSelection({
        enabled: true,
        feedback,
        initialSelectedVoiceId: null,
      })
    );

    await waitFor(() => {
      expect(feedback.warning).toHaveBeenCalledWith('TTS 服务暂不可用，但您仍可选择音色。');
    });

    expect(feedback.error).not.toHaveBeenCalled();
  });
});
