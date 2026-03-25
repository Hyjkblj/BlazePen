// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import TrainingReportStatusNotice from './TrainingReportStatusNotice';

describe('TrainingReportStatusNotice', () => {
  it('shows an in-progress notice when report status is not completed', () => {
    render(<TrainingReportStatusNotice status="in_progress" hasSummary={false} />);

    expect(screen.getByText('报告仍在生成中')).toBeTruthy();
    expect(screen.getByText('in_progress')).toBeTruthy();
  });

  it('returns no notice when report is completed and summary is available', () => {
    const { container } = render(
      <TrainingReportStatusNotice status="completed" hasSummary />
    );

    expect(container.firstChild).toBeNull();
  });

  it('shows a fallback notice when report is completed without summary', () => {
    render(<TrainingReportStatusNotice status="completed" hasSummary={false} />);

    expect(screen.getByText('摘要暂未就绪')).toBeTruthy();
  });
});
