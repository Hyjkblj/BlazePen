// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import { ServiceError } from '@/services/serviceError';
import { useTrainingCharacterPreviewFlow } from './useTrainingCharacterPreviewFlow';

const trainingCharacterApiMocks = vi.hoisted(() => ({
  createTrainingCharacter: vi.fn(),
  createTrainingCharacterPreviewJob: vi.fn(),
  getTrainingCharacterImages: vi.fn(),
  listTrainingIdentityPresets: vi.fn(),
  removeTrainingCharacterBackground: vi.fn(),
  waitForTrainingCharacterPreviewJob: vi.fn(),
}));

vi.mock('@/services/trainingCharacterApi', () => trainingCharacterApiMocks);

type DraftState = {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
};

const createInitialDraft = (): DraftState => ({
  portraitPresetId: 'correspondent-female',
  characterId: '',
  playerName: 'Test Reporter',
  playerGender: 'female',
  playerIdentity: 'field-reporter',
  playerAge: '25',
});

describe('useTrainingCharacterPreviewFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage?.removeItem('training:preview-job:v1');

    trainingCharacterApiMocks.listTrainingIdentityPresets.mockResolvedValue([
      {
        code: 'correspondent-female',
        title: 'Preset',
        description: 'preset',
        identity: 'field-reporter',
        defaultName: 'Test Reporter',
        defaultGender: 'female',
      },
    ]);
    trainingCharacterApiMocks.getTrainingCharacterImages.mockResolvedValue({
      images: [],
    });
  });

  it('should rotate idempotency key after a failed preview retry on the same character', async () => {
    trainingCharacterApiMocks.createTrainingCharacter.mockResolvedValue({
      characterId: '12',
      name: 'Test Reporter',
      imageUrl: null,
      imageUrls: [],
    });

    trainingCharacterApiMocks.createTrainingCharacterPreviewJob
      .mockResolvedValueOnce({
        jobId: 'preview-job-1',
        characterId: '12',
        idempotencyKey: 'preview-key-a1',
        status: 'pending',
        imageUrls: [],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      })
      .mockResolvedValueOnce({
        jobId: 'preview-job-2',
        characterId: '12',
        idempotencyKey: 'preview-key-a2',
        status: 'pending',
        imageUrls: [],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      });

    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob
      .mockResolvedValueOnce({
        jobId: 'preview-job-1',
        characterId: '12',
        idempotencyKey: 'preview-key-a1',
        status: 'failed',
        imageUrls: [],
        errorMessage: 'first attempt failed',
        createdAt: null,
        updatedAt: null,
      })
      .mockResolvedValueOnce({
        jobId: 'preview-job-2',
        characterId: '12',
        idempotencyKey: 'preview-key-a2',
        status: 'succeeded',
        imageUrls: [
          '/static/images/characters/preview_12_1.png',
          '/static/images/characters/preview_12_2.png',
        ],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      });

    function useHarness() {
      const [draft, setDraft] = useState<DraftState>(createInitialDraft());
      const flow = useTrainingCharacterPreviewFlow({
        formDraft: draft,
        onStartTraining: vi.fn(),
        updateFormDraft: (field, value) => {
          setDraft((current) => ({
            ...current,
            [field]: value,
          }));
        },
      });
      return { flow, draft };
    }

    const { result } = renderHook(() => useHarness());

    await waitFor(() => {
      expect(result.current.flow.identityPresetStatus).toBe('ready');
    });

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });

    expect(result.current.flow.previewStatus).toBe('error');

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });

    await waitFor(() => {
      expect(result.current.flow.previewStatus).toBe('ready');
    });

    expect(trainingCharacterApiMocks.createTrainingCharacter).toHaveBeenCalledTimes(1);
    expect(trainingCharacterApiMocks.createTrainingCharacterPreviewJob).toHaveBeenCalledTimes(2);

    const firstIdempotencyKey =
      trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mock.calls[0]?.[0]?.idempotency_key;
    const secondIdempotencyKey =
      trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mock.calls[1]?.[0]?.idempotency_key;

    expect(typeof firstIdempotencyKey).toBe('string');
    expect(typeof secondIdempotencyKey).toBe('string');
    expect(firstIdempotencyKey).not.toBe(secondIdempotencyKey);
  });

  it('should resume existing preview job when create returns typed conflict', async () => {
    trainingCharacterApiMocks.createTrainingCharacter.mockResolvedValue({
      characterId: '12',
      name: 'Test Reporter',
      imageUrl: null,
      imageUrls: [],
    });

    trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mockRejectedValueOnce(
      new ServiceError({
        code: 'TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT',
        status: 409,
        message: 'preview job already exists',
        details: {
          existing_job_id: 'preview-job-existing',
        },
      })
    );

    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob.mockResolvedValueOnce({
      jobId: 'preview-job-existing',
      characterId: '12',
      idempotencyKey: 'preview-conflict-key',
      status: 'succeeded',
      imageUrls: [
        '/static/images/characters/preview_12_1.png',
        '/static/images/characters/preview_12_2.png',
      ],
      errorMessage: null,
      createdAt: null,
      updatedAt: null,
    });

    function useHarness() {
      const [draft, setDraft] = useState<DraftState>(createInitialDraft());
      const flow = useTrainingCharacterPreviewFlow({
        formDraft: draft,
        onStartTraining: vi.fn(),
        updateFormDraft: (field, value) => {
          setDraft((current) => ({
            ...current,
            [field]: value,
          }));
        },
      });
      return { flow, draft };
    }

    const { result } = renderHook(() => useHarness());

    await waitFor(() => {
      expect(result.current.flow.identityPresetStatus).toBe('ready');
    });

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });

    await waitFor(() => {
      expect(result.current.flow.previewStatus).toBe('ready');
    });

    expect(trainingCharacterApiMocks.createTrainingCharacterPreviewJob).toHaveBeenCalledTimes(1);
    expect(trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob).toHaveBeenCalledWith(
      'preview-job-existing',
      expect.any(Object)
    );
    expect(result.current.flow.previewImageUrls).toEqual([
      '/static/images/characters/preview_12_1.png',
      '/static/images/characters/preview_12_2.png',
    ]);
  });

  it('should reuse existing job and idempotency key after poll timeout retry', async () => {
    trainingCharacterApiMocks.createTrainingCharacter.mockResolvedValue({
      characterId: '12',
      name: 'Test Reporter',
      imageUrl: null,
      imageUrls: [],
    });

    trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mockResolvedValueOnce({
      jobId: 'preview-job-timeout',
      characterId: '12',
      idempotencyKey: 'preview-key-timeout-a1',
      status: 'pending',
      imageUrls: [],
      errorMessage: null,
      createdAt: null,
      updatedAt: null,
    });

    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob
      .mockRejectedValueOnce(
        new ServiceError({
          code: 'REQUEST_TIMEOUT',
          status: 408,
          message: 'poll timeout',
          retryable: true,
        })
      )
      .mockResolvedValueOnce({
        jobId: 'preview-job-timeout',
        characterId: '12',
        idempotencyKey: 'preview-key-timeout-a1',
        status: 'succeeded',
        imageUrls: ['/static/images/characters/preview_timeout_12_1.png'],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      });

    function useHarness() {
      const [draft, setDraft] = useState<DraftState>(createInitialDraft());
      const flow = useTrainingCharacterPreviewFlow({
        formDraft: draft,
        onStartTraining: vi.fn(),
        updateFormDraft: (field, value) => {
          setDraft((current) => ({
            ...current,
            [field]: value,
          }));
        },
      });
      return { flow, draft };
    }

    const { result } = renderHook(() => useHarness());

    await waitFor(() => {
      expect(result.current.flow.identityPresetStatus).toBe('ready');
    });

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });
    expect(result.current.flow.previewStatus).toBe('error');

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });

    await waitFor(() => {
      expect(result.current.flow.previewStatus).toBe('ready');
    });

    expect(trainingCharacterApiMocks.createTrainingCharacter).toHaveBeenCalledTimes(1);
    expect(trainingCharacterApiMocks.createTrainingCharacterPreviewJob).toHaveBeenCalledTimes(1);
    expect(trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob).toHaveBeenNthCalledWith(
      1,
      'preview-job-timeout',
      expect.any(Object)
    );
    expect(trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob).toHaveBeenNthCalledWith(
      2,
      'preview-job-timeout',
      expect.any(Object)
    );
  });

  it('should bump retry attempt when characterId already exists and preview status is error', async () => {
    trainingCharacterApiMocks.createTrainingCharacterPreviewJob
      .mockResolvedValueOnce({
        jobId: 'preview-job-existing-1',
        characterId: '12',
        idempotencyKey: 'preview-existing-a1',
        status: 'pending',
        imageUrls: [],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      })
      .mockResolvedValueOnce({
        jobId: 'preview-job-existing-2',
        characterId: '12',
        idempotencyKey: 'preview-existing-a2',
        status: 'pending',
        imageUrls: [],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      });

    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob
      .mockResolvedValueOnce({
        jobId: 'preview-job-existing-1',
        characterId: '12',
        idempotencyKey: 'preview-existing-a1',
        status: 'failed',
        imageUrls: [],
        errorMessage: 'existing character first attempt failed',
        createdAt: null,
        updatedAt: null,
      })
      .mockResolvedValueOnce({
        jobId: 'preview-job-existing-2',
        characterId: '12',
        idempotencyKey: 'preview-existing-a2',
        status: 'succeeded',
        imageUrls: ['/static/images/characters/preview_existing_12_1.png'],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      });

    function useHarness() {
      const [draft, setDraft] = useState<DraftState>({
        ...createInitialDraft(),
        characterId: '12',
      });
      const flow = useTrainingCharacterPreviewFlow({
        formDraft: draft,
        onStartTraining: vi.fn(),
        updateFormDraft: (field, value) => {
          setDraft((current) => ({
            ...current,
            [field]: value,
          }));
        },
      });
      return { flow, draft };
    }

    const { result } = renderHook(() => useHarness());

    await waitFor(() => {
      expect(result.current.flow.identityPresetStatus).toBe('ready');
    });

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });
    expect(result.current.flow.previewStatus).toBe('error');

    await act(async () => {
      await result.current.flow.handleGeneratePreview();
    });

    await waitFor(() => {
      expect(result.current.flow.previewStatus).toBe('ready');
    });

    expect(trainingCharacterApiMocks.createTrainingCharacter).not.toHaveBeenCalled();
    expect(trainingCharacterApiMocks.createTrainingCharacterPreviewJob).toHaveBeenCalledTimes(2);

    const firstIdempotencyKey =
      trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mock.calls[0]?.[0]?.idempotency_key;
    const secondIdempotencyKey =
      trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mock.calls[1]?.[0]?.idempotency_key;

    expect(typeof firstIdempotencyKey).toBe('string');
    expect(typeof secondIdempotencyKey).toBe('string');
    expect(firstIdempotencyKey).not.toBe(secondIdempotencyKey);
  });

  it('should not trust cached characterId before server validates resumed preview job', async () => {
    const draft = createInitialDraft();
    const generationKey = [
      draft.portraitPresetId,
      draft.playerName,
      draft.playerGender,
      draft.playerIdentity,
      draft.playerAge,
    ].join('|');

    globalThis.localStorage?.setItem(
      'training:preview-job:v1',
      JSON.stringify({
        version: 2,
        generationKey,
        characterId: '777',
        attemptNo: 1,
        idempotencyKey: 'preview-cached-a1',
        jobId: 'preview-job-cached',
      })
    );

    let resolveWait: ((value: unknown) => void) | null = null;
    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveWait = resolve;
        })
    );

    function useHarness() {
      const [currentDraft, setDraft] = useState<DraftState>(createInitialDraft());
      const flow = useTrainingCharacterPreviewFlow({
        formDraft: currentDraft,
        onStartTraining: vi.fn(),
        updateFormDraft: (field, value) => {
          setDraft((current) => ({
            ...current,
            [field]: value,
          }));
        },
      });
      return { flow, draft: currentDraft };
    }

    const { result } = renderHook(() => useHarness());

    await waitFor(() => {
      expect(result.current.flow.identityPresetStatus).toBe('ready');
    });
    await waitFor(() => {
      expect(trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob).toHaveBeenCalledWith(
        'preview-job-cached',
        expect.any(Object)
      );
    });
    expect(result.current.draft.characterId).toBe('');

    await act(async () => {
      resolveWait?.({
        jobId: 'preview-job-cached',
        characterId: '12',
        idempotencyKey: 'preview-cached-a1',
        status: 'succeeded',
        imageUrls: ['/static/images/characters/preview_cached_12_1.png'],
        errorMessage: null,
        createdAt: null,
        updatedAt: null,
      });
    });

    await waitFor(() => {
      expect(result.current.flow.previewStatus).toBe('ready');
    });
    expect(result.current.draft.characterId).toBe('12');
  });
});
