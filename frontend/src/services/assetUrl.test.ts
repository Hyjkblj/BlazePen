import { describe, expect, it, vi } from 'vitest';

import { getStaticAssetUrl } from './assetUrl';

describe('getStaticAssetUrl', () => {
  it('keeps absolute urls unchanged', () => {
    expect(getStaticAssetUrl('https://example.com/a.png')).toBe('https://example.com/a.png');
    expect(getStaticAssetUrl('data:image/png;base64,AAA')).toBe('data:image/png;base64,AAA');
  });

  it('returns same-origin path when no static origin configured', () => {
    vi.stubEnv('VITE_STATIC_ASSET_ORIGIN', '');
    expect(getStaticAssetUrl('/static/images/a.png')).toBe('/static/images/a.png');
  });

  it('prefixes /static/* paths with configured static origin', () => {
    vi.stubEnv('VITE_STATIC_ASSET_ORIGIN', 'http://localhost:8010/');
    expect(getStaticAssetUrl('/static/images/a.png')).toBe('http://localhost:8010/static/images/a.png');
  });

  it('does not prefix non-static absolute paths', () => {
    vi.stubEnv('VITE_STATIC_ASSET_ORIGIN', 'http://localhost:8010');
    expect(getStaticAssetUrl('/assets/logo.png')).toBe('/assets/logo.png');
  });
});

