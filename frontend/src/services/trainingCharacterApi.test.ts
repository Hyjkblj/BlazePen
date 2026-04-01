import { beforeEach, describe, expect, it, vi } from 'vitest';
import httpClient, { getErrorData, getErrorStatus, isTimeoutError } from '@/services/httpClient';
import {
  createTrainingCharacterPreviewJob,
  getTrainingCharacterPreviewJob,
  listTrainingIdentityPresets,
  removeTrainingCharacterBackground,
} from './trainingCharacterApi';

vi.mock('@/services/httpClient', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
  getErrorData: vi.fn(),
  getErrorStatus: vi.fn(),
  getErrorMessage: vi.fn((error: unknown) => (error instanceof Error ? error.message : String(error))),
  isTimeoutError: vi.fn(() => false),
  unwrapApiData: vi.fn((value: unknown) => value),
}));

describe('trainingCharacterApi', () => {
  beforeEach(() => {
    vi.mocked(httpClient.post).mockReset();
    vi.mocked(httpClient.get).mockReset();
    vi.mocked(getErrorData).mockReset();
    vi.mocked(getErrorStatus).mockReset();
    vi.mocked(isTimeoutError).mockReset();
    vi.mocked(isTimeoutError).mockReturnValue(false);
  });

  it('normalizes training identity preset payloads', async () => {
    vi.mocked(httpClient.get).mockResolvedValueOnce({
      presets: [
        {
          code: 'correspondent-female',
          title: 'Preset Title',
          description: 'Preset Desc',
          identity: 'field-reporter',
          default_name: 'Preset Name',
          default_gender: 'female',
        },
      ],
    });

    await expect(listTrainingIdentityPresets()).resolves.toEqual([
      {
        code: 'correspondent-female',
        title: 'Preset Title',
        description: 'Preset Desc',
        identity: 'field-reporter',
        defaultName: 'Preset Name',
        defaultGender: 'female',
      },
    ]);
    expect(httpClient.get).toHaveBeenCalledWith('/v1/training/characters/identity-presets', {
      timeout: 30000,
    });
  });

  it('maps preview job 404 query failures into ServiceError', async () => {
    const requestError = new Error('preview job not found');
    vi.mocked(httpClient.get).mockRejectedValueOnce(requestError);
    vi.mocked(getErrorStatus).mockReturnValueOnce(404);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'preview job not found',
      error: { code: 'NOT_FOUND' },
    });

    await expect(getTrainingCharacterPreviewJob('missing-job')).rejects.toMatchObject({
      code: 'NOT_FOUND',
      status: 404,
    });
  });

  it('normalizes preview job attempt observability fields', async () => {
    vi.mocked(httpClient.post).mockResolvedValueOnce({
      job_id: 'preview-job-obs-1',
      character_id: 12,
      idempotency_key: 'preview-obs-key',
      status: 'failed',
      image_urls: [],
      scene_storyline_script: {},
      scene_groups: [],
      scene_generation_status: 'skipped',
      scene_generation_error: null,
      scene_generated_at: null,
      attempt_count: 2,
      last_failed_at: '2026-03-27T20:00:00Z',
      last_error_message: 'provider timeout',
      error_message: 'latest attempt failed',
      created_at: '2026-03-27T19:59:00Z',
      updated_at: '2026-03-27T20:00:00Z',
    });

    await expect(
      createTrainingCharacterPreviewJob({
        character_id: 12,
        idempotency_key: 'preview-obs-key',
        image_type: 'portrait',
        group_count: 2,
      })
    ).resolves.toMatchObject({
      jobId: 'preview-job-obs-1',
      attemptCount: 2,
      lastFailedAt: '2026-03-27T20:00:00Z',
      lastErrorMessage: 'provider timeout',
    });
  });

  it('maps preview job 409 creation failures into typed conflict ServiceError', async () => {
    const requestError = new Error('preview job conflict');
    vi.mocked(httpClient.post).mockRejectedValueOnce(requestError);
    vi.mocked(getErrorStatus).mockReturnValueOnce(409);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'preview job conflict',
      error: {
        code: 'TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT',
        details: {
          existing_job_id: 'preview-job-existing',
        },
      },
    });

    await expect(
      createTrainingCharacterPreviewJob({
        character_id: 12,
        idempotency_key: 'preview-conflict-key',
        image_type: 'portrait',
        group_count: 2,
      })
    ).rejects.toMatchObject({
      code: 'TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT',
      status: 409,
      message: 'preview job conflict',
      details: {
        existing_job_id: 'preview-job-existing',
      },
    });
  });

  it('maps preview job creation timeout into retryable REQUEST_TIMEOUT ServiceError', async () => {
    const timeoutError = new Error('timeout');
    vi.mocked(httpClient.post).mockRejectedValueOnce(timeoutError);
    vi.mocked(isTimeoutError).mockReturnValueOnce(true);
    vi.mocked(getErrorStatus).mockReturnValueOnce(408);
    vi.mocked(getErrorData).mockReturnValueOnce({
      message: 'timeout',
      error: { code: 'REQUEST_TIMEOUT' },
    });

    await expect(
      createTrainingCharacterPreviewJob({
        character_id: 12,
        idempotency_key: 'preview-timeout-key',
        image_type: 'portrait',
        group_count: 2,
      })
    ).rejects.toMatchObject({
      code: 'REQUEST_TIMEOUT',
      status: 408,
      retryable: true,
    });
  });

  it('normalizes remove-background response and drops deprecated local_path', async () => {
    vi.mocked(httpClient.post).mockResolvedValueOnce({
      original_url: '/images/original.png',
      transparent_url: '/images/transparent.png',
      selected_image_url: '/images/original.png',
      local_path: '/tmp/original.png',
    });

    const response = await removeTrainingCharacterBackground('12', {
      imageUrl: '/images/original.png',
      imageUrls: ['/images/original.png'],
      selectedIndex: 0,
    });

    expect(httpClient.post).toHaveBeenCalledWith(
      '/v1/training/characters/12/remove-background',
      {
        image_url: '/images/original.png',
        image_urls: ['/images/original.png'],
        selected_index: 0,
      },
      { timeout: 60000 }
    );
    expect(response).toEqual({
      original_url: '/images/original.png',
      transparent_url: '/images/transparent.png',
      selected_image_url: '/images/original.png',
    });
    expect('local_path' in (response as Record<string, unknown>)).toBe(false);
  });
});

