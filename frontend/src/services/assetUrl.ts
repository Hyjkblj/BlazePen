export const getStaticAssetUrl = (url?: string | null): string => {
  if (!url) return '';

  const value = String(url).trim();
  if (!value) return '';
  if (/^(https?:|data:|blob:|file:)/i.test(value)) return value;

  if (value.startsWith('//')) {
    const protocol = typeof window !== 'undefined' ? window.location.protocol : 'http:';
    return `${protocol}${value}`;
  }

  if (value.startsWith('/')) return value;
  return `/${value.replace(/^\/+/, '')}`;
};
