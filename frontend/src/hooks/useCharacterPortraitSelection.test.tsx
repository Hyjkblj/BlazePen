// @vitest-environment jsdom

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCharacterImages, removeCharacterBackground } from '@/services/characterApi';
import type { CharacterData } from '@/types/game';
import { useCharacterPortraitSelection } from './useCharacterPortraitSelection';

vi.mock('@/services/characterApi', () => ({
  getCharacterImages: vi.fn(),
  removeCharacterBackground: vi.fn(),
}));

const createCharacterDraft = (
  overrides: Partial<CharacterData> = {}
): CharacterData => ({
  characterId: '101',
  name: '测试角色',
  gender: 'female',
  imageUrl: '/portrait-0.png',
  image_urls: ['/portrait-0.png', '/portrait-1.png', '/portrait-2.png'],
  ...overrides,
});

describe('useCharacterPortraitSelection', () => {
  beforeEach(() => {
    vi.mocked(getCharacterImages).mockReset();
    vi.mocked(removeCharacterBackground).mockReset();
  });

  it('repairs deleted portrait placeholders with the transparent portrait snapshot', async () => {
    const updateCharacterDraft = vi.fn();
    const characterDraft = createCharacterDraft({
      transparentImageUrl: '/portrait-transparent.png',
      image_urls: ['portrait_img1.png', 'portrait_img2.png'],
    });

    const { result } = renderHook(() =>
      useCharacterPortraitSelection({
        characterDraft,
        createdCharacterId: '101',
        updateCharacterDraft,
      })
    );

    let loadResult:
      | Awaited<ReturnType<typeof result.current.loadCharacters>>
      | undefined;
    await act(async () => {
      loadResult = await result.current.loadCharacters();
    });

    expect(loadResult?.status).toBe('loaded');
    expect(updateCharacterDraft).toHaveBeenCalledTimes(1);
    expect(result.current.characters[0]?.imageUrls).toEqual(['/portrait-transparent.png']);
    expect(result.current.characters[0]?.imageUrl).toBe('/portrait-transparent.png');
  });

  it('writes the chosen portrait back into the character draft state', async () => {
    let currentDraft = createCharacterDraft();
    const updateCharacterDraft = vi.fn(
      (updater: (current: CharacterData | null) => CharacterData | null) => {
        currentDraft = updater(currentDraft) ?? currentDraft;
      }
    );

    const { result } = renderHook(() =>
      useCharacterPortraitSelection({
        characterDraft: currentDraft,
        createdCharacterId: '101',
        updateCharacterDraft,
      })
    );

    await act(async () => {
      await result.current.loadCharacters();
    });

    let didSelect = false;
    act(() => {
      didSelect = result.current.selectImage('101', 1);
    });

    expect(didSelect).toBe(true);
    expect(currentDraft.selectedCharacterId).toBe('101');
    expect(currentDraft.selectedImageIndex).toBe(1);
    expect(currentDraft.imageUrl).toBe('/portrait-1.png');
  });

  it('returns the normalized portrait draft after background removal succeeds', async () => {
    const characterDraft = createCharacterDraft();

    vi.mocked(removeCharacterBackground).mockResolvedValueOnce({
      original_url: '/portrait-1.png',
      transparent_url: '/portrait-transparent.png',
      selected_image_url: '/portrait-1.png',
    });

    const { result } = renderHook(() =>
      useCharacterPortraitSelection({
        characterDraft,
        createdCharacterId: '101',
        updateCharacterDraft: vi.fn(),
      })
    );

    await act(async () => {
      await result.current.loadCharacters();
    });

    act(() => {
      result.current.selectImage('101', 1);
    });

    const nextDraft = await result.current.prepareSelectedPortrait(characterDraft);

    expect(removeCharacterBackground).toHaveBeenCalledWith(
      '101',
      '/portrait-1.png',
      ['/portrait-0.png', '/portrait-1.png', '/portrait-2.png'],
      1
    );
    expect(nextDraft.transparentImageUrl).toBe('/portrait-transparent.png');
    expect(nextDraft.imageUrl).toBe('/portrait-transparent.png');
    expect(nextDraft.image_urls).toEqual(['/portrait-transparent.png']);
  });
});
