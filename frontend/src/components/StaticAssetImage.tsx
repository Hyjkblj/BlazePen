import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { getStaticAssetUrl } from '@/services/assetUrl';

type AssetLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export interface StaticAssetImageProps {
  imageUrl: string | null | undefined;
  alt: string;
  imageClassName: string;
  placeholderClassName: string;
  placeholder: ReactNode;
  onLoad?: () => void;
  onError?: () => void;
}

export default function StaticAssetImage({
  imageUrl,
  alt,
  imageClassName,
  placeholderClassName,
  placeholder,
  onLoad,
  onError,
}: StaticAssetImageProps) {
  const normalizedUrl = useMemo(() => String(imageUrl ?? '').trim(), [imageUrl]);
  const resolvedSrc = useMemo(() => (normalizedUrl ? getStaticAssetUrl(normalizedUrl) : ''), [normalizedUrl]);
  const [status, setStatus] = useState<AssetLoadState>(normalizedUrl ? 'loading' : 'idle');
  const hasSource = Boolean(normalizedUrl);
  const showImage = hasSource && status !== 'error';
  const showPlaceholder = !hasSource || status !== 'loaded';

  useEffect(() => {
    setStatus(normalizedUrl ? 'loading' : 'idle');
  }, [normalizedUrl]);

  return (
    <>
      {showImage && resolvedSrc ? (
        <img
          key={resolvedSrc}
          src={resolvedSrc}
          alt={alt}
          className={imageClassName}
          onLoad={() => {
            setStatus('loaded');
            onLoad?.();
          }}
          onError={() => {
            setStatus('error');
            onError?.();
          }}
        />
      ) : null}
      {showPlaceholder ? <div className={placeholderClassName}>{placeholder}</div> : null}
    </>
  );
}
