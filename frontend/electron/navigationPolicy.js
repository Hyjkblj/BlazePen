export function normalizeFilePathname(pathname) {
  return pathname.replace(/^\/[A-Za-z]:/, '');
}

export function getBackendProxyPath(requestUrl) {
  try {
    const url = new URL(requestUrl);
    if (url.protocol !== 'file:') {
      return null;
    }

    const pathname = normalizeFilePathname(url.pathname);
    const isApi = pathname === '/api' || pathname.startsWith('/api/');
    const isStatic = pathname === '/static' || pathname.startsWith('/static/');
    const isHealth = pathname === '/health';

    if (isApi || isStatic || isHealth) {
      return `${pathname}${url.search}`;
    }
  } catch {
    return null;
  }

  return null;
}

export function buildBackendRedirectUrl(requestUrl, backendOrigin) {
  const proxyPath = getBackendProxyPath(requestUrl);
  if (!proxyPath) {
    return null;
  }

  try {
    const normalizedOrigin = backendOrigin.replace(/\/+$/, '');
    return new URL(proxyPath, `${normalizedOrigin}/`).toString();
  } catch {
    return null;
  }
}

export function isAllowedWindowNavigation(targetUrl, options) {
  const { isDev, frontendDevOrigin } = options;

  try {
    const url = new URL(targetUrl);

    if (isDev) {
      return url.origin === frontendDevOrigin;
    }

    return url.protocol === 'file:';
  } catch {
    return false;
  }
}
