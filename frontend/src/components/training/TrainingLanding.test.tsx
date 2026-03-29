// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TrainingLanding from './TrainingLanding';

const trainingCharacterApiMocks = vi.hoisted(() => ({
  createTrainingCharacter: vi.fn(),
  createTrainingCharacterPreviewJob: vi.fn(),
  getTrainingCharacterImages: vi.fn(),
  listTrainingIdentityPresets: vi.fn(),
  removeTrainingCharacterBackground: vi.fn(),
  waitForTrainingCharacterPreviewJob: vi.fn(),
}));

vi.mock('@/services/trainingCharacterApi', () => trainingCharacterApiMocks);

describe('TrainingLanding', () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.localStorage?.removeItem('training:preview-job:v1');
    trainingCharacterApiMocks.listTrainingIdentityPresets.mockResolvedValue([
      {
        code: 'correspondent-female',
        title: '战地记者（女）',
        description: '测试预设',
        identity: '战地记者',
        defaultName: '前线女记者',
        defaultGender: 'female',
      },
    ]);
  });

  it('should block preview generation when preset is not selected', async () => {
    render(
      <TrainingLanding
        bootstrapErrorMessage={null}
        bootstrapStatus="idle"
        canStartTraining
        formDraft={{
          portraitPresetId: '',
          characterId: '',
          playerName: '',
          playerGender: '女',
          playerIdentity: '',
          playerAge: '',
        }}
        hasResumeTarget={false}
        resumeSessionId={null}
        onBackToEntryRoute={vi.fn()}
        onManualRestore={vi.fn()}
        onRetryRestore={vi.fn()}
        onStartTraining={vi.fn()}
        updateFormDraft={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(trainingCharacterApiMocks.listTrainingIdentityPresets).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: '生成形象图' }));

    await waitFor(() => {
      expect(screen.getByText('请先选择一个身份预设。')).toBeTruthy();
    });
    expect(trainingCharacterApiMocks.createTrainingCharacter).not.toHaveBeenCalled();
  });

  it('should reuse deterministic idempotency key when retrying same preview request', async () => {
    trainingCharacterApiMocks.createTrainingCharacter.mockResolvedValue({
      characterId: '12',
      name: '测试角色',
      imageUrl: null,
      imageUrls: [],
    });
    trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mockResolvedValue({
      jobId: 'preview-job-1',
      characterId: '12',
      idempotencyKey: 'training-preview-12-1234abcd',
      status: 'pending',
      imageUrls: [],
      errorMessage: null,
      createdAt: null,
      updatedAt: null,
    });
    trainingCharacterApiMocks.waitForTrainingCharacterPreviewJob.mockResolvedValue({
      jobId: 'preview-job-1',
      characterId: '12',
      idempotencyKey: 'training-preview-12-1234abcd',
      status: 'succeeded',
      imageUrls: [
        '/static/images/characters/preview-1.png',
        '/static/images/characters/preview-2.png',
      ],
      errorMessage: null,
      createdAt: null,
      updatedAt: null,
    });

    function StatefulTrainingLanding() {
      const [formDraft, setFormDraft] = useState({
        portraitPresetId: 'correspondent-female',
        characterId: '',
        playerName: '测试用户',
        playerGender: '女',
        playerIdentity: '战地记者',
        playerAge: '25',
      });

      return (
        <TrainingLanding
          bootstrapErrorMessage={null}
          bootstrapStatus="idle"
          canStartTraining
          formDraft={formDraft}
          hasResumeTarget={false}
          resumeSessionId={null}
          onBackToEntryRoute={vi.fn()}
          onManualRestore={vi.fn()}
          onRetryRestore={vi.fn()}
          onStartTraining={vi.fn()}
          updateFormDraft={(field, value) => {
            setFormDraft((current) => ({
              ...current,
              [field]: value,
            }));
          }}
        />
      );
    }

    render(<StatefulTrainingLanding />);

    await waitFor(() => {
      expect(trainingCharacterApiMocks.listTrainingIdentityPresets).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByRole('button', { name: '生成形象图' }));
    await waitFor(() => {
      expect(trainingCharacterApiMocks.createTrainingCharacter).toHaveBeenCalledTimes(1);
      expect(trainingCharacterApiMocks.createTrainingCharacterPreviewJob).toHaveBeenCalledTimes(1);
      expect(screen.getByRole('button', { name: '重新渲染' })).toBeTruthy();
    });

    fireEvent.click(screen.getByRole('button', { name: '重新渲染' }));
    await waitFor(() => {
      expect(trainingCharacterApiMocks.createTrainingCharacter).toHaveBeenCalledTimes(1);
      expect(trainingCharacterApiMocks.createTrainingCharacterPreviewJob).toHaveBeenCalledTimes(2);
    });

    const firstCallKey =
      trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mock.calls[0]?.[0]?.idempotency_key;
    const secondCallKey =
      trainingCharacterApiMocks.createTrainingCharacterPreviewJob.mock.calls[1]?.[0]?.idempotency_key;
    expect(firstCallKey).toBeTruthy();
    expect(firstCallKey).toBe(secondCallKey);
  });
});
