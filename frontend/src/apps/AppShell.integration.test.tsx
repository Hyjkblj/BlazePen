// @vitest-environment jsdom

import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import AppStory from './story/AppStory';
import AppTraining from './training/AppTraining';

describe('app shell separation', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
    window.history.pushState({}, '', '/');
  });

  it('keeps the story app home independent from the training entry', async () => {
    window.history.pushState({}, '', '/');

    render(<AppStory />);

    expect(await screen.findByRole('button', { name: 'BEGIN' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Training Mode' })).toBeNull();
  });

  it('does not register training routes inside the story app shell', async () => {
    window.history.pushState({}, '', '/training');

    render(<AppStory />);

    expect(await screen.findByText('页面不存在')).toBeTruthy();
    expect(screen.queryByText('Training Frontend MVP')).toBeNull();
  });

  it('opens the training frontend from its own app root', async () => {
    window.history.pushState({}, '', '/');

    render(<AppTraining />);

    await waitFor(() => {
      expect(window.location.pathname).toBe('/training');
    });
    expect(await screen.findByText('Training Frontend MVP')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'BEGIN' })).toBeNull();
  });
});
