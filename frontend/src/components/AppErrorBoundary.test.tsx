// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AppErrorBoundary from './AppErrorBoundary';

const telemetrySpy = vi.hoisted(() => vi.fn());

vi.mock('@/services/frontendTelemetry', () => ({
  trackFrontendTelemetry: telemetrySpy,
}));

function ThrowingPanel({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Render exploded.');
  }

  return <div>Recovered panel</div>;
}

function BoundaryHarness() {
  const [shouldThrow, setShouldThrow] = useState(true);

  return (
    <AppErrorBoundary onReset={() => setShouldThrow(false)}>
      <ThrowingPanel shouldThrow={shouldThrow} />
    </AppErrorBoundary>
  );
}

function ResetKeyHarness() {
  const [pathKey, setPathKey] = useState('/training');
  const [shouldThrow, setShouldThrow] = useState(true);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setShouldThrow(false);
          setPathKey('/training/report');
        }}
      >
        Change route
      </button>
      <AppErrorBoundary resetKeys={[pathKey]}>
        <ThrowingPanel shouldThrow={shouldThrow} />
      </AppErrorBoundary>
    </>
  );
}

describe('AppErrorBoundary', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    telemetrySpy.mockReset();
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    consoleErrorSpy.mockRestore();
  });

  it('renders the fallback UI, emits telemetry, and can recover after reset', async () => {
    render(<BoundaryHarness />);

    expect(
      screen.getByRole('heading', { name: 'The app hit an unexpected error.' })
    ).toBeTruthy();
    expect(screen.getByText('Render exploded.')).toBeTruthy();
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.objectContaining({
        domain: 'app',
        event: 'app.render',
        status: 'failed',
      })
    );

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Recovered panel')).toBeTruthy();
  });

  it('automatically resets when resetKeys change', async () => {
    render(<ResetKeyHarness />);

    expect(
      screen.getByRole('heading', { name: 'The app hit an unexpected error.' })
    ).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'Change route' }));

    expect(await screen.findByText('Recovered panel')).toBeTruthy();
  });
});
