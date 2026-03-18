import { useState, type ReactNode } from 'react';
import { getStaticAssetUrl } from '@/services/assetUrl';

type AssetLoadState = 'idle' | 'loading' | 'loaded' | 'error';

export interface StaticAssetImageProps {
  imageUrl: string | null | undefined;
  alt: string;
  imageClassName: string;
  placeholderClassName: string;
  placeholder: ReactNode;
  onError?: () => void;
}

export default function StaticAssetImage({
  imageUrl,
  alt,
  imageClassName,
  placeholderClassName,
  placeholder,
  onError,
}: StaticAssetImageProps) {
  const [status, setStatus] = useState<AssetLoadState>(imageUrl ? 'loading' : 'idle');
  const hasSource = Boolean(imageUrl);
  const showImage = hasSource && status !== 'error';
  const showPlaceholder = !hasSource || status !== 'loaded';

  return (
    <>
      {showImage && imageUrl ? (
        <img
          src={getStaticAssetUrl(imageUrl)}
          alt={alt}
          className={imageClassName}
          style={status === 'loaded' ? undefined : { visibility: 'hidden' }}
          onLoad={() => {
            setStatus('loaded');
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
