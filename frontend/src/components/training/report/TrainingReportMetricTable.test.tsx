// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingReportMetricTable from './TrainingReportMetricTable';

describe('TrainingReportMetricTable', () => {
  it('renders metric rows with formatted values and labels', () => {
    render(
      <TrainingReportMetricTable
        title="八维能力纵览"
        metrics={[
          {
            code: 'K1',
            initial: 0.2,
            final: 0.62,
            delta: 0.42,
            weight: 0.3,
            isLowestFinal: false,
            isHighestGain: true,
          },
        ]}
      />
    );

    expect(screen.getByText('八维能力纵览')).toBeTruthy();
    expect(screen.getByText('史实核验')).toBeTruthy();
    expect(screen.getByText('K1')).toBeTruthy();
    expect(screen.getByText('+0.42')).toBeTruthy();
    expect(screen.getByText('峰值进步 · 计权 0.3')).toBeTruthy();
  });

  it('shows empty state when metrics are not provided', () => {
    render(<TrainingReportMetricTable title="六维态势指数" metrics={[]} />);

    expect(screen.getByText('当前没有指标数据。')).toBeTruthy();
  });
});
