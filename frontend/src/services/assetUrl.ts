export const getStaticAssetUrl = (url?: string | null): string => {
  if (!url) return '';

  const value = String(url).trim();
  if (!value) return '';
  if (/^(https?:|data:|blob:|file:)/i.test(value)) return value;

  const staticAssetOrigin = (import.meta.env.VITE_STATIC_ASSET_ORIGIN ?? '').trim();

  if (value.startsWith('//')) {
    const protocol = typeof window !== 'undefined' ? window.location.protocol : 'http:';
    return `${protocol}${value}`;
  }

  if (value.startsWith('/')) {
    if (staticAssetOrigin && value.startsWith('/static/')) {
      return `${staticAssetOrigin.replace(/\/+$/, '')}${value}`;
    }
    return value;
  }
  return `/${value.replace(/^\/+/, '')}`;
};
