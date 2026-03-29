// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { TrainingScenario } from '@/types/training';
import TrainingRoundPanel from './TrainingRoundPanel';

const createScenario = (options: TrainingScenario['options']): TrainingScenario => ({
  id: 'scenario-1',
  title: '临场采访',
  eraDate: '1941-06-14',
  location: 'Shanghai',
  brief: '根据现场局势完成报道判断。',
  mission: '保护线人并完成发稿。',
  decisionFocus: '在时效和安全之间做出平衡。',
  targetSkills: ['verification'],
  riskTags: ['exposure'],
  options,
  completionHint: '',
  recommendation: null,
});

const createProps = (currentScenario: TrainingScenario | null) => ({
  isCompleted: false,
  currentScenario,
  sessionProgressLabel: '16.7%',
  sceneImageStatus: 'idle' as const,
  sceneImageUrl: null,
  sceneImageErrorMessage: null,
  completionReportStatus: 'idle' as const,
  completionReport: null,
  completionReportErrorMessage: null,
  selectedOptionId: null,
  selectOption: vi.fn(),
  submissionPreview: null,
  canSubmitRound: false,
  submitCurrentRound: vi.fn(),
  retryRestore: vi.fn(),
  clearWorkspace: vi.fn(),
  completedEnding: null,
});

describe('TrainingRoundPanel', () => {
  afterEach(() => {
    cleanup();
  });

  it('uses cinematic choice band for triad options', () => {
    const selectOption = vi.fn();
    const scenario = createScenario([
      { id: 'opt-1', label: '保留一版', impactHint: '先稳住发稿节奏' },
      { id: 'opt-2', label: '继续追问', impactHint: '尝试扩大事实覆盖面' },
      { id: 'opt-3', label: '请求支援', impactHint: '优先降低现场风险' },
    ]);

    render(<TrainingRoundPanel {...createProps(scenario)} selectOption={selectOption} />);

    expect(screen.getByRole('region', { name: 'Training cinematic choices' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /继续追问/i }));
    expect(selectOption).toHaveBeenCalledWith('opt-2');
  });

  it('still uses cinematic choice band for single option scenarios', () => {
    const scenario = createScenario([{ id: 'opt-1', label: '保留一版', impactHint: '先稳住发稿节奏' }]);

    render(<TrainingRoundPanel {...createProps(scenario)} />);

    expect(screen.getByRole('region', { name: 'Training cinematic choices' })).toBeTruthy();
    expect(document.querySelector('.training-shell__option-list .ant-radio-input')).toBeNull();
  });
});
