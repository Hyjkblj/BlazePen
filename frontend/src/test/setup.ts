import { vi } from 'vitest';

const installMatchMediaMock = () => {
  if (typeof window === 'undefined') {
    return;
  }

  const windowWithMatchMedia = window as Window & {
    matchMedia?: typeof window.matchMedia;
  };

  Object.defineProperty(windowWithMatchMedia, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation((query: string) => {
      const mediaQueryList = {
        matches: false,
        media: query,
        onchange: null as ((event: MediaQueryListEvent) => void) | null,
        addListener: vi.fn((listener: (event: MediaQueryListEvent) => void) => {
          listener(mediaQueryList as unknown as MediaQueryListEvent);
        }),
        removeListener: vi.fn(),
        addEventListener: vi.fn(
          (_type: string, listener: ((event: MediaQueryListEvent) => void) | EventListener) => {
            if (typeof listener === 'function') {
              listener(mediaQueryList as unknown as MediaQueryListEvent);
            }
          }
        ),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      };

      return mediaQueryList;
    }),
  });
};

class ResizeObserverMock {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

const installResizeObserverMock = () => {
  if (typeof window === 'undefined') {
    return;
  }

  const globalWithResizeObserver = globalThis as typeof globalThis & {
    ResizeObserver?: typeof ResizeObserver;
  };

  if (typeof globalWithResizeObserver.ResizeObserver === 'function') {
    return;
  }

  Object.defineProperty(globalWithResizeObserver, 'ResizeObserver', {
    configurable: true,
    writable: true,
    value: ResizeObserverMock,
  });
};

installMatchMediaMock();
installResizeObserverMock();
