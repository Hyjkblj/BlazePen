// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TrainingCinematicChoiceBand from './TrainingCinematicChoiceBand';

const createOptions = () => [
  {
    id: 'opt-left',
    label: '保留一版',
    impactHint: '先稳住发稿节奏',
  },
  {
    id: 'opt-top',
    label: '继续追问',
    impactHint: '尝试扩大事实覆盖面',
  },
  {
    id: 'opt-right',
    label: '请求支援',
    impactHint: '优先降低现场风险',
  },
];

describe('TrainingCinematicChoiceBand', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders backend provided option labels and selects by option id', () => {
    const onSelectOption = vi.fn();

    render(
      <TrainingCinematicChoiceBand
        options={createOptions()}
        selectedOptionId={null}
        onSelectOption={onSelectOption}
      />
    );

    expect(screen.getByRole('button', { name: /保留一版/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /继续追问/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /请求支援/i })).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: /继续追问/i }));

    expect(onSelectOption).toHaveBeenCalledWith('opt-top');
  });

  it('supports keyboard navigation and enter-to-select', () => {
    const onSelectOption = vi.fn();

    render(
      <TrainingCinematicChoiceBand
        options={createOptions()}
        selectedOptionId={null}
        onSelectOption={onSelectOption}
      />
    );

    const band = screen.getByRole('region', { name: 'Training cinematic choices' });
    band.focus();

    fireEvent.keyDown(band, { key: 'ArrowRight' });
    fireEvent.keyDown(band, { key: 'Enter' });

    expect(onSelectOption).toHaveBeenCalledWith('opt-top');
  });

  it('renders a view-task button at the lower corner and triggers callback', () => {
    const onSelectOption = vi.fn();
    const onViewTask = vi.fn();

    render(
      <TrainingCinematicChoiceBand
        options={createOptions()}
        selectedOptionId={null}
        onSelectOption={onSelectOption}
        onViewTask={onViewTask}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: '查看任务' }));
    expect(onViewTask).toHaveBeenCalledTimes(1);
  });
});
