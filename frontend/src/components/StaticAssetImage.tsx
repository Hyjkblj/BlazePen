import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { getStaticAssetUrl } from '@/services/assetUrl';

type AssetLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export interface StaticAssetImageProps {
  imageUrl: string | null | undefined;
  alt: string;
  imageClassName: string;
  placeholderClassName: string;
  placeholder: ReactNode;
  preservePreviousImageWhileLoading?: boolean;
  onLoad?: () => void;
  onError?: () => void;
}

export default function StaticAssetImage({
  imageUrl,
  alt,
  imageClassName,
  placeholderClassName,
  placeholder,
  preservePreviousImageWhileLoading = false,
  onLoad,
  onError,
}: StaticAssetImageProps) {
  const normalizedUrl = useMemo(() => String(imageUrl ?? '').trim(), [imageUrl]);
  const resolvedSrc = useMemo(() => (normalizedUrl ? getStaticAssetUrl(normalizedUrl) : ''), [normalizedUrl]);
  const [status, setStatus] = useState<AssetLoadState>(normalizedUrl ? 'loading' : 'idle');
  const [displayedSrc, setDisplayedSrc] = useState<string>('');
  const onLoadRef = useRef(onLoad);
  const onErrorRef = useRef(onError);
  const hasSource = Boolean(normalizedUrl);

  useEffect(() => {
    onLoadRef.current = onLoad;
  }, [onLoad]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    if (preservePreviousImageWhileLoading) return;
    setStatus(normalizedUrl ? 'loading' : 'idle');
  }, [normalizedUrl, preservePreviousImageWhileLoading]);

  useEffect(() => {
    if (!preservePreviousImageWhileLoading) return;

    if (!resolvedSrc) {
      // Keep the previous image while waiting for the next scene source to arrive,
      // so route/phase transitions do not flash a loading placeholder.
      if (!displayedSrc) {
        setStatus('idle');
      }
      return;
    }

    if (displayedSrc === resolvedSrc) {
      return;
    }

    let cancelled = false;
    setStatus('loading');
    const preloader = new Image();
    preloader.src = resolvedSrc;
    preloader.onload = () => {
      if (cancelled) return;
      setDisplayedSrc(resolvedSrc);
      setStatus('loaded');
      onLoadRef.current?.();
    };
    preloader.onerror = () => {
      if (cancelled) return;
      if (!displayedSrc) {
        setStatus('error');
      } else {
        // Keep previous scene frame as fallback to avoid loading flicker.
        setStatus('loaded');
      }
      onErrorRef.current?.();
    };

    return () => {
      cancelled = true;
    };
  }, [resolvedSrc, displayedSrc, preservePreviousImageWhileLoading]);

  const imageSrc = preservePreviousImageWhileLoading ? displayedSrc : resolvedSrc;
  const showImage = Boolean(imageSrc) && status !== 'error';
  const showPlaceholder = preservePreviousImageWhileLoading
    ? !imageSrc
    : !hasSource || status !== 'loaded';

  return (
    <>
      {showImage && imageSrc ? (
        <img
          key={imageSrc}
          src={imageSrc}
          alt={alt}
          className={imageClassName}
          onLoad={() => {
            if (preservePreviousImageWhileLoading) return;
            setStatus('loaded');
            onLoad?.();
          }}
          onError={() => {
            if (preservePreviousImageWhileLoading) return;
            setStatus('error');
            onError?.();
          }}
        />
      ) : null}
      {showPlaceholder ? <div className={placeholderClassName}>{placeholder}</div> : null}
    </>
  );
}
