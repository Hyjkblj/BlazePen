// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useFeedback, useGameFlow } from '@/contexts';
import {
  useCharacterPortraitSelection,
  useCharacterVoiceSelection,
  type CharacterOption,
} from '@/hooks';
import { checkServerHealth } from '@/services/healthApi';
import { ServiceError } from '@/services/serviceError';
import { useCharacterSelectionFlow } from './useCharacterSelectionFlow';

vi.mock('@/contexts', () => ({
  useFeedback: vi.fn(),
  useGameFlow: vi.fn(),
}));

vi.mock('@/hooks', () => ({
  useCharacterPortraitSelection: vi.fn(),
  useCharacterVoiceSelection: vi.fn(),
}));

vi.mock('@/services/healthApi', () => ({
  checkServerHealth: vi.fn(),
}));

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

const createFeedbackSpy = () => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
  dismiss: vi.fn(),
});

const createCharacterOption = (): CharacterOption => ({
  id: '101',
  name: '测试角色',
  gender: 'female',
  imageUrl: '/portrait-1.png',
  imageUrls: ['/portrait-0.png', '/portrait-1.png', '/portrait-2.png'],
});

describe('useCharacterSelectionFlow', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    vi.mocked(checkServerHealth).mockReset();
  });

  it('blocks navigation when the selected voice fails to persist', async () => {
    const feedback = createFeedbackSpy();
    const setCharacterDraft = vi.fn();
    const setCreatedCharacterId = vi.fn();
    const updateCharacterDraft = vi.fn();
    const selectedCharacter = createCharacterOption();
    const nextCharacterDraft = {
      characterId: '101',
      name: '测试角色',
      imageUrl: '/portrait-transparent.png',
      image_urls: ['/portrait-transparent.png'],
      selectedCharacterId: '101',
      selectedImageIndex: 1,
      transparentImageUrl: '/portrait-transparent.png',
    };
    const voicePersistError = new ServiceError({
      code: 'REQUEST_TIMEOUT',
      message: 'Voice config save timed out.',
    });
    const portraitSelectionState = {
      loading: false,
      characters: [selectedCharacter],
      selectedCharacter: '101',
      selectedCharacterOption: selectedCharacter,
      selectedImageIndex: 1,
      selectedImageUrlForVoice: '/portrait-1.png',
      loadCharacters: vi.fn().mockResolvedValue({ status: 'loaded' }),
      selectImage: vi.fn().mockReturnValue(true),
      prepareSelectedPortrait: vi.fn().mockResolvedValue(nextCharacterDraft),
    };
    const voiceSelectionState = {
      presetVoices: [],
      selectedVoiceId: 'voice-1',
      voicesLoading: false,
      previewingVoiceId: null,
      selectVoice: vi.fn(),
      previewVoice: vi.fn(),
      persistSelectedVoiceConfig: vi.fn().mockResolvedValue({
        status: 'failed',
        error: voicePersistError,
      }),
      resetVoicePreview: vi.fn(),
    };

    vi.mocked(useFeedback).mockReturnValue(feedback);
    vi.mocked(useGameFlow).mockReturnValue({
      state: {
        characterDraft: {
          characterId: '101',
          name: '测试角色',
          imageUrl: '/portrait-1.png',
          image_urls: ['/portrait-0.png', '/portrait-1.png', '/portrait-2.png'],
        },
        createdCharacterId: '101',
      },
      setCharacterDraft,
      setCreatedCharacterId,
      updateCharacterDraft,
    } as never);
    vi.mocked(useCharacterPortraitSelection).mockReturnValue(portraitSelectionState);
    vi.mocked(useCharacterVoiceSelection).mockReturnValue(voiceSelectionState);
    vi.mocked(checkServerHealth).mockResolvedValue(true);

    const { result } = renderHook(() => useCharacterSelectionFlow());

    await waitFor(() => {
      expect(portraitSelectionState.loadCharacters).toHaveBeenCalled();
    });

    await act(async () => {
      await result.current.confirmVoice();
    });

    expect(setCharacterDraft).toHaveBeenCalledWith(nextCharacterDraft);
    expect(feedback.error).toHaveBeenCalledWith('音色保存超时，请重试。');
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
